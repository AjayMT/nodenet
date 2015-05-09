
from __future__ import print_function

import sys
from os import path

# weird hack to be able to import nodenet normally
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import nodenet

# make two nodes
n1 = nodenet.node()
n2 = nodenet.node()

# bind nodes to ports
n1.bind('127.0.0.1', 3000)
n2.bind('127.0.0.1', 3001)


# set up event handlers
def on_hello(who, data):
    print(str(who) + ': ' + str(data))
    n1.emit('foo', 'bar')


def on_connect(*args):
    n2.emit('hello', {'hello': 'world'})

n1.on('hello', on_hello)
n2.on('foo', print)
n2.on('connect', on_connect)

# connect nodes to each other
# every connection is two-way, so only one node has to (and should) connect
n2.connect(n1)

# start the event loop
nodenet.loop.run()

# output:
# ('127.0.0.1', 3001): {u'hello': u'world'}
# ('127.0.0.1', 3000) bar
