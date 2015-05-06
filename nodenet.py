
import json
from pyuv import Loop, TCP
from emitter import Emitter


class Node(TCP, Emitter):
    def __init__(self, loop):
        TCP.__init__(self, loop)
        Emitter.__init__(self)

        self.conns = []

    def iferr(self, *args):
        err = args[-1]

        if err:
            super(Node, self).emit('error', err)

    def ondata(self, handle, data, err):
        self.iferr(err)

        data = str(data)
        try:
            msg = json.loads(data)
            super(Node, self).emit(msg['name'], *msg['args'])
        except:
            self.handshake(handle, data, err)

    def handshake(self, handle, data, err):
        def cb(handle, err):
            self.iferr(err)

            super(Node, self).emit('connect', data)

        conns, clients = zip(*self.conns)
        if data.startswith('host?'):
            host, port = self.getsockname()
            handle.write('host=' + host + ':' + str(port))

            return

        if data.startswith('host='):
            data = tuple(data.split('=')[1].split(':'))
            data = (data[0], int(data[1]))

            if data not in conns:
                host, port = self.getsockname()
                handle.write('host;' + host + ':' + str(port))

                self.connect(data, cb)

            return

        if data.startswith('host;'):
            data = data.split(';')[1].split(':')
            data = (data[0], int(data[1]))
            super(Node, self).emit('connect', data)

    def listen(self, backlog=511):
        def cb(server, err):
            self.iferr(err)

            client = TCP(self.loop)
            self.accept(client)

            host, port = self.getsockname()
            client.write('host?' + host + ':' + str(port))
            client.start_read(self.ondata)

        super(Node, self).listen(cb, backlog)
        super(Node, self).emit('listening', self.getsockname())

    def connect(self, args, cb=None):
        if not cb:
            cb = self.iferr

        conns, clients = zip(*self.conns)
        if args in conns:
            return

        c = TCP(self.loop)
        c.connect(args, cb)
        c.start_read(self.ondata)

        self.conns.append((args, c))

    def emit(self, event, *args, **kwargs):
        msg = json.dumps({'name': event, 'args': args})

        for conn, client in self.conns:
            if not conn or not client:
                continue

            if conn == kwargs.get('to') or not kwargs.get('to'):
                client.write(msg)
