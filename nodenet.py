
import json
import signal
import pyuv as uv
from emitter import Emitter

loop = uv.Loop.default_loop()


def node():
    return Node(loop)


class Node(uv.UDP, Emitter):
    def __init__(self, loop):
        uv.UDP.__init__(self, loop)
        Emitter.__init__(self)

        self._sigint_h = uv.Signal(self.loop)
        self._sigterm_h = uv.Signal(self.loop)
        self._sigint_h.start(self.close, signal.SIGINT)
        self._sigterm_h.start(self.close, signal.SIGTERM)

        self._conns = []

    def _check_err(self, *args):
        err = args[-1]
        if err:
            super(Node, self).emit('error', err, uv.errno.strerror(err))

    def _on_data(self, handle, who, flags, data, err):
        if data is None:
            return

        self._check_err(err)

        data = str(data).encode('utf-8')
        try:
            msg = json.loads(data)
            super(Node, self).emit(msg['name'], *msg['args'])
        except:
            if data.startswith('connect;'):
                data = tuple(data.split(';')[1].split(':'))
                data = (data[0], int(data[1]))
                if data not in self._conns:
                    self._conns.append(data)
                    super(Node, self).emit('connect', data)

                return

            if data.startswith('close;'):
                super(Node, self).emit('disconnect', who)
                self._conns.remove(who)

    def close(self, *args):
        super(Node, self).emit('close', args[-1])

        [self.send(conn, 'close;', self._check_err) for conn in self._conns]

        self.stop_recv()
        self._sigint_h.close()
        self._sigterm_h.close()
        super(Node, self).close()

    def bind(self, *where):
        super(Node, self).bind(where)
        self.start_recv(self._on_data)
        super(Node, self).emit('bind', self.getsockname())

    def connect(self, *who):
        def cb(handle, err):
            self._check_err(err)
            super(Node, self).emit('connect', who)

        if who in self._conns:
            return

        self._conns.append(who)

        host, port = self.getsockname()
        super(Node, self).send(who, 'connect;' + host + ':' + str(port), cb)

    def emit(self, event, *args, **kwargs):
        msg = json.dumps({'name': event, 'args': args})

        for conn in self._conns:
            if kwargs.get('to') == conn or not kwargs.get('to'):
                self.send(conn, msg, self._check_err)
