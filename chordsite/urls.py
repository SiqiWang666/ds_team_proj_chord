"""chordsite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from chordsite import views
from chordsite.views import Chord
from django.conf import settings
from django.conf.urls.static import static

from chordsite.views import set_head
from chordsite.node import Node
from chordsite.util import local_ip

import os

global head
head = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

urlpatterns = [
    path('', Chord.as_view()),
    path('admin/', admin.site.urls),
    path('create_ring/', views.create_ring),
    path('get_all_finger/', views.get_all_finger),
    # path('add_node/', views.add_node),
    # path('lookup/', views.lookup),
    # path('remove_node/', views.remove_node),
    path('list_dir/', views.list_dir),
    path('save_file/', views.save_file),
    path('get_file/', views.get_file),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# start the Node instance on current machine using its ip
def one_time_startup():
    # head refers to the Node instance of this machine itself,
    # since the Chord ring is like a linked list, we call it head
    global head
    ip_arr = []
    f= open(os.path.abspath(os.path.join(BASE_DIR, '../node_addr')), 'r')

    for ip in f:
        i = ip.strip()
        if i:
            ip_arr.append(i)

    print('ip_arr: ', ip_arr)

    # if the first ip is not local
    # try:
    #     os.environ['NODE_STARTED']
    # except KeyError:
    local = local_ip()
    if ip_arr[0] == local:
        head = Node(ip_arr[0])
    else:
        head = Node(local, ip_arr[0])

        # os.environ['NODE_STARTED'] = "NODE_STARTED"

    set_head(head)

one_time_startup()
