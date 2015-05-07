
import json
import signal
from pyuv import Loop, TCP, Signal
from emitter import Emitter


def node():
    return Node(Loop.default_loop())


class Node(TCP, Emitter):
    def __init__(self, loop):
        TCP.__init__(self, loop)
        Emitter.__init__(self)

        self._sigint_h = Signal(self.loop)
        self._sigterm_h = Signal(self.loop)
        self._sigint_h.start(self.close, signal.SIGINT)
        self._sigterm_h.start(self.close, signal.SIGTERM)

        self._conns = []

    def _iferr(self, *args):
        err = args[-1]

        if err:
            super(Node, self).emit('error', err)

    def _ondata(self, handle, data, err):
        if data is None:
            return

        self._iferr(err)

        data = str(data)
        try:
            msg = json.loads(data)
            super(Node, self).emit(msg['name'], *msg['args'])
        except:
            self._handshake(handle, data, err)

    def _handshake(self, handle, data, err):
        def cb(handle, err):
            self._iferr(err)

            super(Node, self).emit('connect', data)

        conns, clients = zip(*(self._conns or [(None, None)]))
        if data.startswith('host?'):
            host, port = self.getsockname()
            handle.write('host=' + host + ':' + str(port))

            return

        if data.startswith('host='):
            data = tuple(data.split('=')[1].split(':'))
            data = (data[0], int(data[1]))

            if data not in conns:
                host, port = self.getsockname()
                handle.write(';' + host + ':' + str(port))

                self.connect(data, cb)

            return

        if data[0] == ';':
            data = data[1:].split(':')
            data = (data[0], int(data[1]))
            super(Node, self).emit('connect', data)

            return

        if data.startswith('close;'):
            data = tuple(data.split(';')[1].split(':'))
            data = (data[0], int(data[1]))
            [c.close() for conn, c in self._conns if conn == data]
            self._conns = [c for c in self._conns if not conn == data]

    def close(self, *args):
        super(Node, self).emit('close', args[-1])

        conns, clients = zip(*(self._conns or [(None, None)]))
        clients = [c for c in clients if c]
        host, port = self.getsockname()

        [c.write('close;' + host + ':' + str(port)) for c in clients]
        [c.close() for c in clients if c]

        self._sigint_h.close()
        self._sigterm_h.close()
        super(Node, self).close()

    def listen(self, args, backlog=511):
        def cb(server, err):
            self._iferr(err)

            client = TCP(self.loop)
            self.accept(client)

            client.write('host?')
            client.start_read(self._ondata)

        super(Node, self).bind((args))
        super(Node, self).listen(cb, backlog)
        super(Node, self).emit('listening', self.getsockname())

    def connect(self, args, cb=None):
        if not cb:
            cb = self._iferr

        conns, clients = zip(*(self._conns or [(None, None)]))
        if args in conns:
            return

        c = TCP(self.loop)
        c.connect(args, cb)
        c.start_read(self._ondata)

        self._conns.append((args, c))

    def emit(self, event, *args, **kwargs):
        msg = json.dumps({'name': event, 'args': args})

        for conn, client in self._conns:
            if not conn or not client:
                continue

            if conn == kwargs.get('to') or not kwargs.get('to'):
                client.write(msg)
