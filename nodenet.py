
import json
import signal
import pyuv as uv
from emitter import Emitter


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
        self.peers = []

        self.on('disconnect', self._on_disconnect)

        self._current = None
        self._queue = []
        self._sigint_h = uv.Signal(self.loop)
        self._sigterm_h = uv.Signal(self.loop)
        self._sigint_h.start(self.close, signal.SIGINT)
        self._sigterm_h.start(self.close, signal.SIGTERM)

    def _check_err(self, *args):
        err = args[-1]
        if err:
            super(Node, self).emit('error', err, uv.errno.strerror(err))

    def _on_disconnect(self, who):
        self.peers.remove(who)

        if self._current is None:
            return

        msg, to, cb = self._current
        if who in to:
            to.remove(who)

        if len(to) == 0:
            self._next_event(self, None)

    def _protocol(self, who, data):
        if 'connect;' in data:
            version = data.split(';')[1]

            if not version == self.protocol_version:
                self.send(who, 'speak;' + self.protocol_version,
                          self._check_err)

                return

            if who not in self.peers:
                self.peers.append(who)
                self.send(who, 'connected;', self._check_err)
                super(Node, self).emit('connect', who)

            return

        if 'speak;' in data:
            errno, msg = ERRNO['ERR_PROTOCOL_VERSION']
            super(Node, self).emit('error', errno, msg)

            return

        if data == 'connected;':
            self.peers.append(who)
            super(Node, self).emit('connect', who)

            return

        if data == 'rcvd;' and self._current is not None:
            msg, to, cb = self._current

            to.remove(who)
            if len(to) == 0:
                self._next_event(self, None)

            else:
                self._current = (msg, to, cb)

            return

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

    def _next_event(self, h, e):
        msg, to, cb = self._current
        cb(h, e)

        if len(self._queue) > 0:
            self._current = self._queue.pop(0)
            self._emit_next()

        else:
            self._current = None

    def _emit_next(self):
        msg, to, callback = self._current

        [self.send(who, msg, self._check_err) for who in to]

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

        if who in self.peers:
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
            kwargs['to'] = self.peers

        kwargs['to'] = [n.sockname if type(n) is Node else n
                        for n in kwargs['to']]
        kwargs['to'] = [n for n in kwargs['to'] if n in self.peers]

        if kwargs['to'] == []:
            kwargs['cb'](self, None)
            return

        msg = json.dumps({'name': event, 'args': args})

        if self._current is None:
            self._current = (msg, kwargs['to'], kwargs['cb'])
            self._emit_next()

        else:
            self._queue.append((msg, kwargs['to'], kwargs['cb']))
