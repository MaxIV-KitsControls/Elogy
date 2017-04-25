Elogy
=====

*Under development, not suitable for actual use*.

This is a web-based electronic lab logbook application. It allows users to write down notes about what they are doing, organize them and access them later. Intended for use on an internal network; no security features.

Quite inspired by "elog" from PSI, in terms of features. Includes some (unreliable) scripts that can be used to import data from an elog installation.

The backen is based on Python and Flask, using SQLite to store data. The frontend is written in React.


Building
========

Since the frontend is built in JavaScript/ES6, it needs to be built in order to be useful. This can be done by entering the `elogy/frontend` directory and entering
```
$ npm install
$ npm run build
```

To run a development proxy server with "hot reload" etc, run
```
$ npm start
```
It assumes that you've started the server on port 8000 (see below).

Installation
============

Requires Python 3.x (currently only tested with 3.5, 3.4 should work.)

To run with flask's built-in development server:
```
$ python -m venv env
$ env/bin/pip install -r requirements.txt
$ env/bin/pip install -e .
$ FLASK_APP=elogy ELOGY_CONFIG_FILE=$(pwd)/config.py env/bin/flask run -p 8000
```

For actual deployment you probably want to run it with something else, such as:
```
$ gunicorn -k gevent --threads 3 elogy:app
```

Also have a look in ```config.py``` for further settings.


Features (present and planned)
==============================

* Simple, useful GUI
* JSON HTTP API
* Stand-alone service (no external databases and stuff)
* All changes are logged
* No user authentication
* Search/filter on everything


Design philosophy
=================

Keep it simple. Focus on core functionality, extend through the API if possible instead of blindly adding features. Maintainability counts!

Don't add dependencies without a good reason. Ease of installation is important.

Stick to modern web standards, but don't worry too much about backwards compatibility. For now testing in recent versions of Firefox/Chrome will do.

Don't make things configurable unless absolutely necessary. Configuration adds code complexity, cases that need testing, etc.

Try to postpone performance optimizations until it's clear they are really needed.


Ideas
=====

* Push updates via SSE/websockets? This might replace the need for configurable actions, email etc.
* The ORM (peewee) supports other backends like postgres. Something to consider.
* Text search in sqlite is quite limited. Maybe look into an embedded search engine like whoosh?
* A basic mobile version would be neat!
