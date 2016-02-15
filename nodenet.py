
import json
import signal
import pyuv as uv
from emitter import Emitter
from uuid import uuid4


ERRNO = {'ERR_PROTOCOL_VERSION': (1, 'wrong protocol version')}
loop = uv.Loop.default_loop()


def _nest_cbs(times, fn, args, step, final):
    if not times:
        return

    args = list(args)

    def cb(*a):
        step(*a)
        _nest_cbs(times - 1, fn, args, step, final)

    if times == 1:
        cb = final

    fn(*(args + [cb]))


class Node(uv.UDP, Emitter):
    def __init__(self, loop=loop):
        """A nodenet node.

        Arguments:
        loop -- a pyuv event loop
        """
        uv.UDP.__init__(self, loop)
        Emitter.__init__(self)

        self.protocol_version = '0.2.0'
        self.sockname = (None, None)
        self.queue_messages = True

        self._peers = {}
        self._sigint_h = uv.Signal(self.loop)
        self._sigterm_h = uv.Signal(self.loop)
        self._sigint_h.start(self.close, signal.SIGINT)
        self._sigterm_h.start(self.close, signal.SIGTERM)

    def _check_err(self, *args):
        err = args[-1]
        if err:
            super(Node, self).emit('error', err, uv.errno.strerror(err))

    def _protocol(self, who, data):
        if data.startswith('connect;'):
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

        if data.startswith('speak;'):
            errno, msg = ERRNO['ERR_PROTOCOL_VERSION']
            super(Node, self).emit('error', errno, msg)

            return

        if data == 'connected;':
            self._peers[who] = []
            super(Node, self).emit('connect', who)

            return

        if data == 'disconnect;':
            del self._peers[who]
            super(Node, self).emit('disconnect', who)

            return

        if not self.queue_messages:
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

        data = str(data)
        try:
            msg = json.loads(data)
            super(Node, self).emit(msg['name'], who, *msg['args'])
            self.send(who, 'rcvd;', self._check_err)

        except:
            self._protocol(who, data)

    @property
    def peers(self):
        return self._peers.keys()

    def flush(self, peer):
        """Empty the message queue for a single peer.

        Arguments:
        peer -- the peer node whose message queue to empty
        """
        peer = peer.sockname if type(peer) is Node else peer
        self._queue[who] = []

    def close(self, *args):
        """Close the node.

        Arguments:
        signum -- an optional signal number that is passed to listeners for
          the 'close' event
        """
        i = []

        def step(i, err):
            self._check_err(err)
            i.append(None)

        def cb(h, e):
            self._check_err(e)
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

        if self.peers:
            # TODO: get rid of len(i) hack
            _nest_cbs(len(self.peers), self.send,
                      [self.peers[len(i)], 'disconnect;'],
                      lambda h, e: step(i, e), cb)

        else:
            cb(self, None)

            return

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
        node -- another instance of `Node` to connect to. If this is supplied,
          other arguments are ignored.
        ip -- IP address of node.
        port -- port number of node.
        flowinfo -- optional flow info, only for IPv6. Defaults to 0.
        scope_id -- optional scope ID, only for IPv6. Defaults to 0.
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
        to=None -- optional keyword argument. A list of specific nodes to
          emit the event to. Each element in the list is a (host, port) tuple,
          or an instance of Node. If this is None, the event is broadcast
          to all connected nodes. Defaults to None.
        cb=None -- optional keyword argument. A callback to call after the
          event has been emitted. Called with two arguments: the Node instance
          that emitted the event, and an error object. If this is None, the
          error is handled by emitting an 'error' event if necessary. Defaults
          to None.
        """
        i = []

        def step(h, e):
            self._check_err(e)
            i.append(None)

        if 'cb' not in kwargs:
            kwargs['cb'] = self._check_err

        if 'to' not in kwargs:
            kwargs['to'] = self._peers

        kwargs['to'] = [n.sockname if type(n) is Node else n
                        for n in kwargs['to']]
        kwargs['to'] = [n for n in kwargs['to'] if n in self.peers]

        if kwargs['to'] == []:
            kwargs['cb'](self, None)
            return

        msg = json.dumps({'name': event, 'args': args})
        uid = str(uuid4())

        if not self.queue_messages:
            # TODO: get rid of len(i) hack
            _nest_cbs(len(kwargs['to']), self.send,
                      [kwargs['to'][len(i)], msg],
                      lambda h, e: step(i, e), kwargs['cb'])

            return

        for peer in kwargs['to']:
            self._peers[peer].append((msg, uid, kwargs['cb']))

            if len(self._peers[peer]) == 1:
                self.send(peer, msg, self._check_err)
