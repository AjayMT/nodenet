
# nodenet
[![Build Status](https://travis-ci.org/AjayMT/nodenet.svg)](https://travis-ci.org/AjayMT/nodenet)

nodenet is an asynchronous, event-driven, node-based UDP networking library for python.

**This is still a work in progress. Read the TODO section.**

## 'node-based'?
(No, I don't mean [node.js](http://nodejs.org).)

nodenet is centered around **nodes** rather than clients and servers. Each node is bound to a port and can connect to an arbitrary number of other nodes, and all of them can exchange messages in the form of 'events'. All that a node *actually* is is an extension of [pyuv's UDP handler](http://pyuv.readthedocs.org/en/latest/udp.html).

## Installation
```sh
$ easy_install nodenet
```
or
```sh
$ git clone http://github.com/AjayMT/nodenet.git && cd nodenet
$ python setup.py install
```

## Running tests
```sh
$ ./test
```

## TODO
- lots of docs
- better tests

## License
MIT License. See `./LICENSE` for details.
