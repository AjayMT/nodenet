
import sys
from os import path

# weird hack to be able to import nodenet normally
sys.path.append(
    path.dirname(path.dirname(path.abspath(__file__)))
)

import nodenet
from pyvows import expect

n1 = nodenet.Node()
n2 = nodenet.Node()
n3 = nodenet.Node()

n1.bind('127.0.0.1', 3000)
n2.bind('127.0.0.1', 3001)
n3.bind('127.0.0.1', 3002)


def test(*args):
    sendcount = []

    def on_data(who, data):
        print '  ' + str(who) + ': ' + data
        expect(data).to_equal('test')
        expect(who).to_equal(n2.sockname)

        sendcount.append(data)
        if len(sendcount) > 1:
            print 'test failed: on_data called too many times'
            n1.close(None)
            n2.close(None)
            n3.close(None)
            sys.exit(1)

    n2.on('data', on_data)
    n3.on('data', on_data)

    print '\ntesting multicast...'
    n1.emit('data', 'test', to=[n2])

n3.on('connect', test)
n2.on('connect', lambda who: n3.connect(n1))
n2.connect(n1)

nodenet.loop.run()
