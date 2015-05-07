
# nodenet
nodenet is an

- asynchronous
- event-driven
- node-based

UDP networking library for python (with a [nice API](http://github.com/ajaymt/nodenet/blob/master/example.py)).

**This is still a work in progress. Read the TODO section.**

## 'node-based'?
(No, I don't mean [node.js](http://nodejs.org).)

nodenet is centered around **nodes** rather than clients and servers (hence the name). Each node is bound to a port and can connect to an arbitrary number of other nodes, and all of them can exchange messages in the form of 'events'. All that a node *actually* is is an extension of [pyuv's UDP handler](http://pyuv.readthedocs.org/en/latest/udp.html).

## TODO
- docs
- docs
- more docs
- lots of tests
- make a setup.py and publish the module

## License
MIT License. See `./LICENSE` for details.
