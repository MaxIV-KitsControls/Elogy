Elogy
=====

*Under development, not suitable for actual use*.

This is a web-based electronic lab logbook application. It allows users to write down notes about what they are doing, organize them and access them later. Intended for use on an internal network; no security features.

Quite inspired by "elog" from PSI, in terms of features. Includes some (unreliable) scripts that can be used to import data from an elog installation.

Based on Python and Flask, using SQLite to store data.


Installation
============

Requires python 3.x (currently only tested with 3.5, 3.4 should work.)

$ pip -r requirements.txt
$ python run.py

Also have a look in config.py for the settings.


Features (present and planned)
==============================

* Simple, useful GUI
* HTTP API
* Stand-alone service (no external databases and stuff)
* All changes are logged
* No user authentication
* Search/filter on everything


Design philosophy
=================

Keep it simple. Focus on core functionality, extend through the API if possible instead of blindly adding features. Maintainability counts!

Don't add dependencies without a good reason. Ease of installation is important.

Prefer HTML/CSS techniques over JavaScript (within reason). Render pages on the server.

Stick to modern web standards, but don't worry too much about backwards compatibility. For now testing in recent versions of Firefox/Chrome will do.

Don't make things configurable unless absolutely necessary. Configuration adds code complexity, cases that need testing, etc.

Try to postpone performance optimizations until it's clear they are really needed.


Ideas
=====

* Cache rendered pages and serve statically [optimization!]
* Push updates via SSE/websockets? This might replace the need for configurable actions, email etc.
* The ORM (peewee) supports other backends like postgres. Something to consider.
* Text search in sqlite is quite limited. Maybe look into an embedded search engine like whoosh?
* A basic mobile version should be pretty easy.
