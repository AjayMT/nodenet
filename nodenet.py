
import json
import signal
import pyuv as uv
from emitter import Emitter
from uuid import uuid4


ERRNO = {'ERR_PROTOCOL_VERSION': (1, 'wrong protocol version')}
loop = uv.Loop.default_loop()


class Node(uv.UDP, Emitter):
    def __init__(self, loop=loop):
        """A nodenet node.

        Arguments:
        loop -- a pyuv event loop to run on
        """
        uv.UDP.__init__(self, loop)
        Emitter.__init__(self)

        self.protocol_version = '0.1.0'
        self.sockname = (None, None)

        self.on('disconnect', self._on_disconnect)

        self._peers = {}
        self._sigint_h = uv.Signal(self.loop)
        self._sigterm_h = uv.Signal(self.loop)
        self._sigint_h.start(self.close, signal.SIGINT)
        self._sigterm_h.start(self.close, signal.SIGTERM)

    def _check_err(self, *args):
        err = args[-1]
        if err:
            super(Node, self).emit('error', err, uv.errno.strerror(err))

    def _on_disconnect(self, who):
        del self._peers[who]

    def _protocol(self, who, data):
        if 'connect;' in data:
            version = data.split(';')[1]

            if not version == self.protocol_version:
                self.send(who, 'speak;' + self.protocol_version,
                          self._check_err)

                return

            if who not in self._peers:
                self._peers[who] = []
                self.send(who, 'connected;', self._check_err)
                super(Node, self).emit('connect', who)

            return

        if 'speak;' in data:
            errno, msg = ERRNO['ERR_PROTOCOL_VERSION']
            super(Node, self).emit('error', errno, msg)

            return

        if data == 'connected;':
            self._peers[who] = []
            super(Node, self).emit('connect', who)

            return

        if data == 'rcvd;' and who in self._peers:
            msg = self._peers[who][0]

            del self._peers[who][0]

            pending = [queue for peer, queue in self._peers.items()
                       if msg in queue]

            if not pending:
                msg[2](self, None)

            if self._peers[who]:
                self.send(who, self._peers[who][0][0], self._check_err)

    def _on_data(self, handle, who, flags, data, err):
        if data is None:
            return

        self._check_err(err)

        data = str(data).encode('utf-8')
        try:
            msg = json.loads(data)
            super(Node, self).emit(msg['name'], who, *msg['args'])
            self.send(who, 'rcvd;', self._check_err)

        except:
            self._protocol(who, data)

    @property
    def peers(self):
        return self._peers.keys()

    def close(self, *args):
        """Close the node.

        Arguments:
        signum -- an optional signal number that is passed to listeners for
          the 'close' event
        """
        def cb(h, e):
            if self.closed:
                return

            self._check_err(e)
            self.stop_recv()
            self._sigint_h.close()
            self._sigterm_h.close()
            super(Node, self).close()

        if not len(args):
            args = [None]

        super(Node, self).emit('close', args[-1])
        self.emit('disconnect', cb=cb)

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

        if who in self._peers:
            return

        self.send(who, 'connect;' + self.protocol_version, self._check_err)

    def emit(self, event, *args, **kwargs):
        """Emit an event.

        Arguments:
        event -- event name
        *args -- arguments to pass to event listeners
        to=None -- optional keyword argument, a list of specific nodes to
          emit the event to. Each element in the list is a tuple like the one
          passed to Node#connect, or an instance of Node. If this is None, the
          event is broadcast to all connected nodes. Defaults to None.
        cb=None -- optional keyword argument, a callback to call after the
          event has been emitted. Called with two arguments: the Node instance
          that emitted the event, and an error object. If this is None, the
          error is handled by emitting an 'error' event if necessary. Defaults
          to None.
        """
        if 'cb' not in kwargs:
            kwargs['cb'] = self._check_err

        if 'to' not in kwargs:
            kwargs['to'] = self._peers

        kwargs['to'] = [n.sockname if type(n) is Node else n
                        for n in kwargs['to']]
        kwargs['to'] = [n for n in kwargs['to'] if n in self._peers]

        if kwargs['to'] == []:
            kwargs['cb'](self, None)
            return

        msg = json.dumps({'name': event, 'args': args})
        uid = str(uuid4())

        for peer in kwargs['to']:
            self._peers[peer].append((msg, uid, kwargs['cb']))

            if len(self._peers[peer]) == 1:
                self.send(peer, msg, self._check_err)
