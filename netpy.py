
import json
from pyuv import Loop, TCP
from emitter import Emitter


class Node(TCP, Emitter):
    def __init__(self, loop):
        TCP.__init__(self, loop)
        Emitter.__init__(self)

        self.conns = []
        self.clients = []

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
            self.onconnect(handle, data, err)

    def onconnect(self, handle, data, err):
        def cb(handle, err):
            self.iferr(err)

            super(Node, self).emit('connect', data)

        if data.startswith('host?'):
            host, port = self.getsockname()
            handle.write('host=' + host + ':' + str(port))

            if handle not in self.clients:
                self.clients.append(handle)

            return

        if data.startswith('host='):
            data = tuple(data.split('=')[1].split(':'))
            data = (data[0], int(data[1]))

            if data not in self.conns:
                host, port = self.getsockname()
                handle.write('host;' + host + ':' + str(port))
                self.connect(data, cb)
                self.conns.append(data)

                if handle not in self.clients:
                    self.clients.append(handle)

            return

        if data.startswith('host;'):
            data = data.split(';')[1].split(':')
            data = (data[0], int(data[1]))
            super(Node, self).emit('connect', data)

    def listen(self, backlog=511):
        def cb(server, err):
            client = TCP(self.loop)
            self.accept(client)

            client.write('host?')
            client.start_read(self.ondata)

        super(Node, self).listen(cb, backlog)
        super(Node, self).emit('listening', self.getsockname())

    def connect(self, args, cb=None):
        if not cb:
            cb = self.iferr

        c = TCP(self.loop)
        c.connect(args, cb)
        c.start_read(self.ondata)

        self.conns.append(args)

    def emit(self, event, *args):
        msg = json.dumps({'name': event, 'args': args})
        for c in self.clients:
            c.write(msg)
