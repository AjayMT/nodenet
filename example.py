
from __future__ import print_function
from nodenet import Node
from pyuv import Loop

# make an event loop
loop = Loop.default_loop()

# make two nodes
n1 = Node(loop)
n2 = Node(loop)

# bind nodes to ports
n1.bind(('127.0.0.1', 3000))
n2.bind(('127.0.0.1', 3001))

# connect nodes to each other
n1.connect(('127.0.0.1', 3001))
n2.connect(('127.0.0.1', 3000))


def on_hello(data):
    print (data)
    n1.emit('foo', 'bar')

# set up event handlers
n1.on('hello', on_hello)
n2.on('foo', print)

# emit events
n2.emit('hello', {'hello': 'world'})

# start the event loop
loop.run()

# output:
# {u'hello': u'world'}
# bar
