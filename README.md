This repository contains an adaption of Johan Forsberg's https://github.com/johanfforsberg/elogy.

Installation
============
1. `git clone git@gitlab.maxiv.lu.se:kits-ims/elogy.git`
2. Modify `docker-compose.yml`.
3. Run `docker-compose up`

Structure
=========
This deployment uses three docker containers: frontend, backend and balancer.

                       __________[frontend:80]
                      /    /*
                     /
    --->[balancer:80]
                     \
                      \__________[backend:80]
                         /api/*

Todo
====
* Verify that docker-less local development and testing is easy

# Original README.md

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

Also required is the `JSON1` extension to sqlite, which is an optional compile time option that is fairly new, and may or may not be enabled in your installation. It's available by default in recent Ubuntu versions, at least. If not, one way to get a compatible version is to use the "Anaconda" python distribution and installing `sqlite` from the `conda-forge` channel. If you don't want the whole distribution you can install "miniconda".

To run elogy with flask's built-in development server, on port 8000:
```
$ python -m venv env
$ env/bin/pip install -r requirements.txt
$ env/bin/pip install -e .
$ FLASK_APP=elogy.app ELOGY_CONFIG_FILE=$(pwd)/config.py env/bin/flask run -p 8000
```

For actual deployment you probably want to run it with something else, such as:
```
$ gunicorn -k gevent --threads 3 elogy.app:app
```

Or possibly using uWSGI+nginx or something. There is lots of documentation out there on how to deploy Flask applications in different scenarios.

Also have a look in ```config.py``` for further settings.


Testing
=======

There is a rudimentary test suite. Using `pytest`:

```
$ pytest test/
```

Features (present and planned)
==============================

* Simple, useful GUI
* JSON HTTP API for all functionality
* Stand-alone service (no external databases and stuff)
* Changes are logged (and reversible)
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

* Push updates via SSE/websockets? This might replace the need for configurable actions, email etc. How about RSS?
* The ORM (peewee) supports other backends like postgres. Something to consider.
* Text search in sqlite is quite limited. Maybe look into an embedded search engine like whoosh?
* A basic mobile version would be neat!


API
===

The HTTP API is pretty simple; it basically allows to read and write logbooks and entries using JSON. It's quite rough right now and is subject to change, but the basics are there. E.g. (examples use `httpie`):

```
$ http localhost:8000/api/logbooks/4/
```

Returns an object `{"logbook": {...logbook-short}}` where the inner object is a nested tree of "logbook-short" objects with the following structure:

```
  {
     "id": 4,
     "name": "My logbook",
     "description": "A very nice logbook!",
     ...
     "children": [
         {...logbook-short},
         {...logbook-short},
         ...
     ]
  }
```
However, if the logbook id (4) is omitted in the URL, you will get the whole tree of existing logbooks, and the top level logbook will have all fields set to null except "children". It's the "null" logbook so it does not really exist, but it's still included for consistency. (Note: maybe this should change...)

The information included in the `logbook-short` objects is an abbreviated version for display purposes, that excludes things like attributes.

To have a peek at the entries in a logbook, you can do:

```
  $ http localhost:8000/api/logbook/4/entries/
  
  {
      "logbook": {...logbook},
      "count": 46,
      "entries": [
          {
              "id": 45,
              "title": "This is an entry!",
              "authors": ["Author Authorsson", ...],
              "content": "This is the first X00 characters of the entry contents. Blabla..."
              "created_at": "Thu, 09 Feb 2017 18:47:00 -0000",
              "logbook": {
                  "id": 4,
                  "name": "My logbook",
              },
              "n_attachments": 0,
              "n_followups": 1,
              ...
          },
          {...entry-short},
          ...
      ]
  }
```
  
The URL can be extended with query parameters (such as `?content=beam%20dump&authors=joe`) to filter the results included to those matching the query. The parameters can contain regular expressions. You can also include e.g. `n=100` and `offset=50` to get only a given part of the list. The entries are currently always sorted by creation/modification date, descending order.
  
Again, the `entry-short` object is again a shorter version of the full information, intended to be used in e.g. displaying a list of entries.
  
Then to get a full entry, do:

```
  $ http localhost:8000/api/logbook/4/entries/45/
  
  {
     "entry": {
         "id": 47,
         "title": "This is another entry!",
         "authors": [{"name": "Author Authorsson", "login": "autaut"}, {...author}],
         "logbook": {...logbook-full},
         ...
     }
  }
```

To post a new entry, basically just do a POST to e.g. `localhost:8000/api/logbook/4/entries/` with a suitable JSON object like above (but without the wrapping `"entry"`). To update an existing entry, you do PUT to `localhost:8000/api/logbook/4/entries/47/`.

Same principle works for writing logbooks.

Previous versions of an entry are available by appending e.g. `/revisions/0` to the entry's URL. That will retrieve the original version, the revision number increments by one each time the entry is edited. If you omit the revision number, you instead get a list of the changes between each revision.

There are also some other parts of the API:

`/api/attachments/` can currently only be used for uploading attachments. It accepts form data since it needs to receive binary files. At some point it should be possible to query for information about a given attachment. For downloading an attachment file, the `/attachments/...` route should be used as it serves the files statically. Of course, ideally attachments should be served by a dedicated webserver instead.
  
`/api/users/` is just a convenience feature for finding proper author names. It looks in LDAP if configured, or the system's password and group files to find users matching a search string. Probably not very useful outside the frontend.

There are some basic API tests that may provide helpful hints. 


Admin interface
===============

There is a simple, generic database interface accessible at `/admin`. It's not protected in any way and can quite easily be used to corrupt the database. It's currently only recommended for use as a read only debugging tool.
