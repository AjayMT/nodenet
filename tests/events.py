
import sys
from os import path

# weird hack to be able to import nodenet normally
sys.path.append(
    path.dirname(path.dirname(path.abspath(__file__)))
)

import nodenet
from pyvows import expect

print '\ntesting events...'

n1 = nodenet.Node()
n2 = nodenet.Node()


def passevent(events, name, index, value):
    events[name][index] = value


def runtest(events, n1, n2):
    try:
        expect(events['bind']).to_equal([n1.sockname, n2.sockname])
        expect(events['connect']).to_equal([n2.sockname, n1.sockname])
        expect(events['close/disconnect']).to_equal([-2, n1.sockname])
        expect(n2.peers).Not.to_include(n1.sockname)
        print '  passed:'
        print '    ' + str(events)
        print '    ' + str(n2.peers)

    except Exception as e:
        print '  failed: ' + str(e)
        nodenet.loop.stop()
        sys.exit(1)

events = {
    'bind': [False, False],
    'connect': [False, False],
    'close/disconnect': [False, False]
}

n1.on('bind', lambda x: passevent(events, 'bind', 0, x))
n2.on('bind', lambda x: passevent(events, 'bind', 1, x))

n1.on('connect', lambda x: passevent(events, 'connect', 0, x))
n2.on('connect', lambda x: passevent(events, 'connect', 1, x))

n1.on('connect', lambda x: n1.close(-2))

n1.on('close', lambda x: passevent(events, 'close/disconnect', 0, x))
n2.on('disconnect', lambda x: passevent(events, 'close/disconnect', 1, x))

n1.on('close', lambda x: n1.emit('closing'))

n2.on('disconnect', lambda x: runtest(events, n1, n2))

n1.bind('127.0.0.1', 3000)
n2.bind('127.0.0.1', 3001)

n1.connect(n2)

nodenet.loop.run()
