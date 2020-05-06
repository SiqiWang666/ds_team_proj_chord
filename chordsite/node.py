#!/bin/python
import sys
import random
import math
import threading
import rpyc


from chordsite.env import *
from chordsite.address import inrange
from chordsite.finger_entry import FingerEntry
# from rpc_server import RPC
# from rpc_client import RPCClient
from rpyc.utils.server import ThreadedServer

# class representing a local peer

# class Node(object):
class Node(rpyc.Service):
    def __init__(self, local_address, remote_address=None):
        self._address = local_address

        # a hash map of rpc client to remote nodes, key is ip, value is the client
        self.remote_clients = {}

        # get identifier
        _id = self._address.__hash__() % NUM_SLOTS

        """
        avoid collision
        TODO: find through remote_node to see if other node has the same id
        """
        # while remote.getRemoteNodeByID(_id) is not None:
        if remote_address is not None:
            while self.get_remote_node(remote_address).node_id() == _id:
                _id = (_id + 1) % NUM_SLOTS
        self._id = _id

        # initialize successor
        self._successor = None

        # list of successors is to prevent lookup failure
        self._successors = [None for x in range(M_BIT)]
        self._predecessor_id = _id
        self._successor_id = _id

        # initialize predecessor
        self._predecessor = None

        # finger table
        self._finger = None
        self._leave = False

        # means that node in on the ring
        # TODO: to be removed when using RPC, DEPRECATED
        # self._remote.addToNetwork(self._id, self)

        # join the DHT
        self.join(remote_address)

        # in case any node depatures
        # self.check_predecessor()

        # initilize RPC server
        # thread = ThreadedServer(RPC(self), hostname='0.0.0.0', port=18861, protocol_config={
        #     'allow_all_attrs': True
        # })
        # self._thread = threading.Thread(target=thread.start)
        # self._thread.start()
        # print('RPC server started...')


        # initilize RPC server
        thread = ThreadedServer(self, hostname='0.0.0.0', port=18861, protocol_config={
            'allow_all_attrs': True,
            'allow_setattr': True,
            'allow_delattr': True,
        })
        self._thread = threading.Thread(target=thread.start)
        self._thread.start()
        print('RPC server started...')

    def address(self):
        return self._address

    def exposed_address(self):
        return self._address


    # node leave
    def leave(self):
        self._leave = True
        # exit(0)


    # logging function
    def log(self, info):
        f = open("/tmp/chord.log", "a+")
        f.write(str(self.node_id()) + " : " + info + "\n")
        f.close()
        print(str(self.node_id()) + " : " + info)


    # return true if node does not leave, i.e. still in the Chord ring
    def ping(self):
        if self._leave:
            return False
        return True

    def exposed_ping(self):
        if self._leave:
            return False
        return True


    def get_remote_node(self, ip):
        if ip not in self.remote_clients:
            # self.remote_clients[ip] = RPCClient(ip)
            self.remote_clients[ip] = rpyc.connect(ip, 18861)

        return self.remote_clients[ip].root


    """
    find the exact successor by comparing the hash(n), can be regarded as a lookup
    1. initialize the predecessor and the finger table
    2. notify other nodes to update their predecessors and finger tables
    3. the new node takes over its responsible keys from its successor.
    """
    def join(self, remote_address=None):
        # initialize finger table
        self._finger = [None for x in range(M_BIT)]

        if remote_address:
            # 1) add to a node `n`, n.find_successor(`to_be_added`)
            start = (self.node_id() + (2 ** 0)) % NUM_SLOTS

            # TODO: replace _remote.getRemoteNode method, start a RPC client instead
            # remote_node = self._remote.getRemoteNode(remote_address)
            # find rpc client to remote node
            remote_node = self.get_remote_node(remote_address)
            print('remote_node: ', remote_node)

            # TODO: RPC call find_successor, calling RPC server function
            # successor = remote_node.find_successor(start)
            # find remote node by Chord ID
            # successor = remote_node.find_succ(start)
            successor = remote_node.find_successor(start)

            self._finger[0] = FingerEntry(start, successor)

            # 2) point `to_be_added`’s `successor` to the node found
            self._successor = successor

            # 3) copy keys less than `ID(to_be_added)` from the `successor`
            # self._predecessor = successor._predecessor
            self._predecessor = successor.predecessor()

            # update its successor's predecessor
            # self._successor._predecessor = self
            self._successor.set_predecessor(self)

        else:
            # current node is the first node on the Chord ring
            self._successor = self
            # self._finger[0] = FingerEntry(self.id(), self)
            self._predecessor = self

        # add other entries in finger table
        self.init_finger(remote_address)

        self.fix_finger()

        self.update_successors()

        # # 4) call `to_be_added`.stabilize() to update the nodes between `to_be_added` and its predecessor
        self.stabilize()

        self.log("joined")


    # ---------------------------------------------


    """
    first node on circle that succeeds (n + 2^k−1) mod 2m, 1 <= k <= m
    i-th entry means the 2^i far-away node from the current node
    """
    def init_finger(self, remote_address=None):
        if remote_address:
            # get the arbitrary node in which the target node want to join
            # TODO: _remote.getRemoteNode _remote with RPC client
            # remote_node = self._remote.getRemoteNode(remote_address)
            remote_node = self.get_remote_node(remote_address)

            # first find its successor, i.e. the first entry in its finger table
            successor = self.successor()
            if successor is None:
                # TODO: replace with RPC call find_succ
                successor = remote_node.find_successor(self.node_id())
                self._successor = successor

            # initialize the rest of its finger table
            for x in range(1, M_BIT):
                start_id = (self.node_id() + 2 ** x) % NUM_SLOTS
                self._finger[x] = FingerEntry(start_id, None)

            # find the corresponding nodes that are supposed to be in the finger table
            for x in range(0, M_BIT - 1):
                start_id = self._finger[x + 1].start

                if inrange(start_id, self.node_id(), self._finger[x].node.node_id()):
                    # if inrange, no RPC call needed, assign locally
                    self._finger[x + 1].node = self._finger[x].node
                else:
                    """
                    need to call find successor leveraging finger table
                    for `self.find_successor`, if its the first node
                    """
                    successor = self.find_successor(start_id)
                    self._finger[x + 1] = FingerEntry(start_id, successor)

        else:
            # n is the only node in the network
            for x in range(0, M_BIT):
                start_id = math.floor((self.node_id() + 2 ** x) % NUM_SLOTS)
                self._finger[x] = FingerEntry(start_id, self)

        self.print_finger('init_finger')


    # ---------------------------------------------

    # called periodically
    # back-up successor list, a M_BIT-long successor link list
    def update_successors(self):
        if self._leave:
            return

        successor = self._successor

        for x in range(M_BIT):
            if successor is not None:
                self._successors[x] = successor
                successor = successor.successor()

        threading.Timer(2, self.update_successors).start()


    def node_id(self, offset=0):
        return self._id


    def exposed_node_id(self, offset=0):
        return self._id



    # for successor other than the node itself, `successor` returns the Netrefs instance of a remote node
    def successor(self):
        successor = self._successor
        print('current successor', self._successor.ping())

        if not successor.ping():
            for x in range(1, len(self._successors)):
                if self._successors[x].ping():
                    successor = self._successors[x]

        print('current successor', successor.node_id())

        return successor

    def exposed_successor(self):
        successor = self._successor
        print('current successor', self._successor.ping())

        if not successor.ping():
            for x in range(1, len(self._successors)):
                if self._successors[x].ping():
                    successor = self._successors[x]

        print('current successor', successor.node_id())

        return successor


    # for predecessor other than the node itself, `predecessor` returns the Netrefs instance of a remote node
    def predecessor(self):
        return self._predecessor

    def exposed_predecessor(self):
        return self._predecessor

    def get_succ_pred_id(self):
        print('get_succ_pred_id: ', self._successor.node_id(), self._predecessor_id)
        return (self._successor.node_id(), self._predecessor_id)

    def exposed_get_succ_pred_id(self):
        print('exposed_get_succ_pred_id: ', self._successor.node_id(), self._predecessor_id)
        return (self._successor.node_id(), self._predecessor_id)

    # set predecessor
    def set_predecessor(self, node):
        print('---------set_predecessor------------')
        print(node.node_id())
        self._predecessor_id = node.node_id()


    # TODO: one thing to note is this may return a Netrefs instance of a remote node, rather than a Node instance
    def find_successor(self, id):
        print('---------find_successor--------------')
        self.log("find_successor of {}".format(id))
        # if self._predecessor exists, and _predecessor.id < id < self.id, the successor is current node
        pre_id = self._predecessor.node_id()
        self_id = self.node_id()
        if self._predecessor and inrange(id, pre_id, self_id):
            return self

        # TODO: replace `find_predecessor` and `successor` with RPC call
        return self.find_predecessor(id).successor()


    def find_predecessor(self, id):
        lg = "find_predecessor of: {}".format(id)
        self.log(lg)
        node = self
        # when the ring only has one node, node.id is the same as node.successor.id,
        # if we are alone in the ring, we are the pred(id)
        if node.node_id() == node.successor().node_id():
            return node
        while not inrange(id, node.node_id(), node.successor().node_id() + 1):
            node = node._closest_preceding_node(id)
        return node


    def _closest_preceding_node(self, id):
        # from m down to 1
        for x in reversed(range(len(self._finger))):
            entry = self._finger[x]
            # TODO: replace id method with RPC call, maybe a new method to replace _closest_preceding_node
            if entry != None and entry.node != None and inrange(entry.node.node_id(), self.node_id(), id):
                return entry.node

        return self

    # used for network visualization application
    def get_finger(self):
        finger = []
        for x in range(len(self._finger)):
            if self._finger[x] is not None:
                finger.append(
                    {'start': self._finger[x].start, 'node': self._finger[x].node.node_id()})
            else:
                finger.append({})

        return str(finger)

    # used for network visualization application
    def exposed_get_finger(self):
        return self.get_finger()


    def update_finger(self, successor, index):
        if self._finger[index] is not None:
            if inrange(successor.node_id(), self.node_id() - 1, self._finger[index].node.node_id()):
                self._finger[index].node = successor
                # TODO: replace `update_finger` with a RPC call
                self._predecessor.update_finger(successor, index)
                # print('finger table of ', self.id(), 'start: ', self._finger[x].start, 'node', self._finger[x].node.id())


    # DEPRECATED


    def update_others(self):
        for x in range(1, M_BIT + 1):
            # find last node whose i-th finger might be current node
            start = (self.node_id() - 2 ** (x - 1)) % NUM_SLOTS

            """
            2 cases for such invocations:
            - returns a Node instance when only one node in the network
            - returns a Netref instance of a remote node
            """
            pre = self.find_predecessor(start)

            # if only one node on the ring, no need to update others
            if pre.node_id() == self.node_id():
                continue
            pre.update_finger(self, x)


    # called periodically
    # clear the node’s predecessor pointer if n.predecessor is alive, or has failed
    def check_predecessor(self):
        if self._leave:
            return

        # self.log('check_predecessor, predecessor of {}: , isAlive: {}'.format(self.predecessor().id(), self.predecessor().ping()))
        pre = self.predecessor()
        if pre is not None and not pre.ping():
            self._predecessor = None

        threading.Timer(2, self.check_predecessor).start()


    # called periodically
    # check its own successor if any new node added between its previous successor
    def stabilize(self):
        if self._leave:
            return
        # prevent successor failure
        successor = self.successor()

        # pre = successor._predecessor
        pre = successor.predecessor()
        print('-----------stabilize--------------')
        pre_id = pre.node_id()
        self_id = self.node_id()
        succ_id = successor.node_id()

        if pre is not None and inrange(pre_id, self_id, succ_id):
            self.log('stabilize calls update_successor')
            self.update_successor(pre)

        print('stabilize successor: ', successor.notify)
        successor.notify(self)
        self.print_finger('stabilize')

        threading.Timer(2, self.stabilize).start()


    # RPC call
    # receive request that some node thinks it might be our predecessor
    def notify(self, pre):
        # check if pre is the new predecessor
        if (self._predecessor is None or inrange(pre.node_id(), self._predecessor.node_id(), self.node_id())):
            self._predecessor = pre


    def exposed_notify(self, pre):
        # check if pre is the new predecessor
        if (self._predecessor is None or inrange(pre.node_id(), self._predecessor.node_id(), self.node_id())):
            self._predecessor = pre


    # called periodically
    # randomly update finger table
    def fix_finger(self):
        if self._leave:
            return
        self.log('fix_finger')
        index = random.randrange(M_BIT - 1) + 1
        self._finger[index].node = self.find_successor(
            self._finger[index].start)
        # self.print_finger('fix_finger')

        threading.Timer(2, self.fix_finger).start()


    # update both first entry in finger table and _successor
    def update_successor(self, new_s):
        self._successor = new_s
        self._finger[0].node = new_s


    def print_finger(self, mod='default'):
        for x in range(0, M_BIT):
            if self._finger[x] is not None:
                self.log('{}: finger table of {}, start: {}, node: {}'.format(
                    mod, self.node_id(), self._finger[x].start, self._finger[x].node.node_id()))


# if __name__ == "__main__":
    # thread = ThreadedServer(RPC(self), hostname='0.0.0.0', port=18861, protocol_config={
    #     'allow_all_attrs': True
    # })
    # self._thread = threading.Thread(target=thread.start)
    # self._thread.start()
    # print('RPC server started...')