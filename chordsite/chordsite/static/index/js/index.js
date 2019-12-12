const $container = $('#container .circle-container');
const $tip = $('#tip');

let fingers;

$tip.text('Creating Chord ring...');
$.get('/create_ring', function (data) {
    return data
}).done(function (data) {
    startRender()

    $('#lookup').on('click', (e) => {
        const key = $('#lookup_key').val();
        const onNode = $('#on_node').val();
        if (key == undefined || onNode == undefined) {
            alert('Please input key and node id');
            return
        }

        if (!fingers.shape[onNode]) {
            alert('That slot has no node');
            return
        }
        $.get(`/lookup?key=${key}&id=${onNode}`, function (data) {
            alert(`Key found at Node ${data.target}`);
        })
    })

    $('#add_node').on('click', (e) => {
        const ip = $('#add_node_ip').val();
        if (!validateIp(ip)) {
            return
        }

        $.get(`/add_node?ip=${ip}`, (data) => {
            render(data);
            $tip.text(`node ${ip} added`)
        });
    })

    $('#leave_node').on('click', (e) => {
        const id = $('#leave_node_id').val();
        if (!id) {
            alert('Please input the right node id');
        }

        $.get(`/remove_node?id=${id}`, (data) => {
            render(data);
            $tip.text(`node ${id} leaves`)
        })
    })
})

function render(data) {
    fingers = data;
    const numOfLot = Math.pow(2, data.m || 3);
    const lots = [];
    const shape = fingers.shape
    
    for(let i = 0; i < numOfLot; i++) {
        const dot = $(`<div ${shape[i] != null ? 'class="active"' : ''} node_id=${i}>
            <span style="color: red">${i}</span>
        </div>`);
        const deg = (360 / numOfLot) * i;
        dot.css('transform', `rotate(${deg}deg) translate(16.5em) rotate(-${deg}deg)`)
        lots.push(dot);
    }

    const nodeInfo = $('#node_info');

    $container.on('mouseover', '.active', (e) => {
        const current = $(e.target).attr('node_id');
        const info = fingers.shape[current];

        let fingerTable = info.finger.reduce((prev, cur) => {
            prev.push(`
                <span>start: ${cur.start}</span>
                <span>node: ${cur.node}</span>
                </br>
            `);
            return prev;
        }, []);

        let node = `<div>
            <p>ID: ${current}</p>
            <p>Address ${JSON.parse(info.addr).join(':')}</p>
            <p>Finger Table:</p>
            <p>${fingerTable.join('')}</p>
        </div>`;

        nodeInfo.html(node);
    })

    $container.on('mouseout', '.active', (e) => {
        nodeInfo.html('Hover on a node to view details');
    })

    $container.html(lots)
}

function validateIp(ipaddress) {
    if (/^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/.test(ipaddress)) {
        return (true)
    }
    alert("You have entered an invalid IP address!")
    return (false)
}

function startRender() {
    setInterval(() => {
        $.get('/get_all_finger', function (data) {
            $tip.text('');
            render(data);
        })
    }, 1000)
}