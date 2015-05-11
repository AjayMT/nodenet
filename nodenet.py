
import json
import signal
import pyuv as uv
from emitter import Emitter

loop = uv.Loop.default_loop()


def node():
    """Returns a node initialised with the default event loop (nodenet.loop)"""
    return Node(loop)


class Node(uv.UDP, Emitter):
    def __init__(self, loop):
        """A nodenet node.

        Arguments:
        loop -- a pyuv event loop to run on
        """
        uv.UDP.__init__(self, loop)
        Emitter.__init__(self)

        self.sockname = (None, None)

        self._sigint_h = uv.Signal(self.loop)
        self._sigterm_h = uv.Signal(self.loop)
        self._sigint_h.start(self.close, signal.SIGINT)
        self._sigterm_h.start(self.close, signal.SIGTERM)

        self.peers = []

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
            super(Node, self).emit(msg['name'], who, *msg['args'])

        except:
            if data.startswith('connect;'):
                data = tuple(data.split(';')[1].split(':'))
                data = (data[0], int(data[1]))
                if data not in self.peers:
                    host, port = self.sockname
                    self.peers.append(data)
                    self.send(data, 'connected;' + host + ':' + str(port),
                              self._check_err)
                    super(Node, self).emit('connect', data)

                return

            if data.startswith('connected;'):
                data = tuple(data.split(';')[1].split(':'))
                data = (data[0], int(data[1]))
                self.peers.append(data)
                super(Node, self).emit('connect', data)

                return

            if data.startswith('close;'):
                super(Node, self).emit('disconnect', who)
                self.peers.remove(who)

    def close(self, *args):
        """Close the node.

        Arguments:
        signum -- an optional signal number that is passed to listeners for
          the 'close' event
        """
        if not len(args):
            args = [None]

        super(Node, self).emit('close', args[-1])

        [self.send(conn, 'close;', self._check_err) for conn in self.peers]

        self.stop_recv()
        self._sigint_h.close()
        self._sigterm_h.close()
        super(Node, self).close()

    def bind(self, *where):
        """Bind to a port.

        Arguments:
        host -- IP address of host
        port -- port number
        flowinfo -- optional flow info, only for IPv6. Defaults to 0.
        scope_id -- optional scope ID, only for IPv6. Defaults to 0.
        """
        self.sockname = where
        super(Node, self).bind(self.sockname)
        self.start_recv(self._on_data)
        super(Node, self).emit('bind', self.sockname)

    def connect(self, *who):
        """Connect to a node.

        Arguments:
        node -- another instance of `Node` to connect to. Mutually exclusive of
          all other arguments.
        ip -- IP address of node. Mutually exclusive of `node`.
        port -- port number of node. Mutually exclusive of `node`.
        flowinfo -- optional flow info, only for IPv6. Defaults to 0. Mutually
          exclusive of `node`.
        scope_id -- optional scope ID, only for IPv6. Defaults to 0. Mutually
          exclusive of `node`.
        """
        if type(who[0]) is Node:
            who = who[0].sockname

        if who in self.peers:
            return

        host, port = self.sockname
        self.send(who, 'connect;' + host + ':' + str(port), self._check_err)

    def emit(self, event, *args, **kwargs):
        """Emit an event.

        Arguments:
        event -- event name
        *args -- arguments to pass to event listeners
        to=None -- optional keyword argument, a list of specific nodes to
          emit the event to. Each element in the list is a tuple like the one
          passed to Node#connect, or an instance of Node. If this is None, the
          event is broadcast to all connected nodes. Defaults to None.
        """
        if not kwargs.get('to'):
            kwargs['to'] = self.peers

        kwargs['to'] = [n.sockname if type(n) is Node else n
                        for n in kwargs['to']]
        kwargs['to'] = [n for n in kwargs['to'] if n in self.peers]

        msg = json.dumps({'name': event, 'args': args})
        for conn in kwargs['to']:
            self.send(conn, msg, self._check_err)
