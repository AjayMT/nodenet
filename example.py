
from __future__ import print_function
import nodenet

# make two nodes
n1 = nodenet.node()
n2 = nodenet.node()

# bind nodes to ports
n1.bind('127.0.0.1', 3000)
n2.bind('127.0.0.1', 3001)

# connect nodes to each other
n1.connect('127.0.0.1', 3001)
n2.connect('127.0.0.1', 3000)


def on_hello(data):
    print(data)
    n1.emit('foo', 'bar')

# set up event handlers
n1.on('hello', on_hello)
n2.on('foo', print)

# emit events
n2.emit('hello', {'hello': 'world'})

# start the event loop
nodenet.loop.run()

# output:
# {u'hello': u'world'}
# bar
