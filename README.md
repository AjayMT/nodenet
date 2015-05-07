
# nodenet
A node-based asynchronous event-driven networking library for python.

**This is still a work in progress. Read the TODO section.**

## 'node-based'?
(No, I don't mean [node.js](http://nodejs.org).)

nodenet is centered around **nodes** rather than clients and servers. Each node is bound to a port and can connect to an arbitrary number of other nodes, and all of them can exchange messages in the form of 'events'. The network itself is built on top of UDP.

## TODO
- docs
- docs
- more docs
- lots of tests
- make a setup.py and publish the module

## License
MIT License. See `./LICENSE` for details.
