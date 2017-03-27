Elogy
=====

*Under development, not suitable for actual use*.

This is a web-based electronic lab logbook application. It allows users to write down notes about what they are doing, organize them and access them later. Intended for use on an internal network; no security features.

Quite inspired by "elog" from PSI, in terms of features. Includes some (unreliable) scripts that can be used to import data from an elog installation.

Based on Python and Flask, using SQLite to store data.


Installation
============

Requires Python 3.x (currently only tested with 3.5, 3.4 should work.)

In order to get WYSIWYG editing features, you need to grab a copy of the TinyMCE editor widget, unzip it and copy the `tinymce/js/tinymce` directory into `elogy/static`. I recommend  http://download.ephox.com/tinymce/community/tinymce_4.4.3.zip instead of the latest version since, at the time of writing, it has a bug affecting the 'list' toolbar buttons (see https://github.com/tinymce/tinymce/issues/3342).

To run with flask's built-in development server:
```
$ python -m venv env
$ env/bin/pip install -r requirements.txt
$ env/bin/pip install -e .
$ FLASK_APP=elogy ELOGY_CONFIG_FILE=$(pwd)/config.py env/bin/flask run
```

For actual deployment you probably want to run it with something else, such as:
```
$ gunicorn -k gevent --threads 3 elogy:app
```

Also have a look in ```config.py``` for the settings.


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
