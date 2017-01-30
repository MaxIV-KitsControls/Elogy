from datetime import datetime
import json
from jinja2 import TemplateNotFound

from .db import Entry, Logbook
from flask import (Blueprint, abort, redirect, render_template, request,
                   url_for)
from peewee import JOIN, fn, DoesNotExist


entries = Blueprint('entries', __name__)


@entries.route("/<int:entry_id>")
def show_entry(entry_id):
    entry = Entry.get(Entry.id == entry_id)
    return render_template("entry.html", entry=entry, **request.args)


@entries.route("/new")
def new_entry():
    "Deliver a form for posting a new entry"
    data = request.args
    follows_id = int(data.get("follows", 0))
    if follows_id:
        follows = Entry.get(Entry.id == follows_id)
        logbook = follows.logbook
    else:
        follows = None
        logbook_id = int(data["logbook"])
        logbook = Logbook.get(Logbook.id == logbook_id)
    return render_template('edit_entry.html',
                           logbook=logbook, follows=follows)


@entries.route("/edit/<int:entry_id>")
def edit_entry(entry_id):
    "Deliver a form for posting a new entry"
    entry = Entry.get(Entry.id == entry_id)
    if entry.follows:
        follows = Entry.get(Entry.id == entry.follows)
    else:
        follows = 0
    logbook = entry.logbook
    return render_template('edit_entry.html',
                           entry=entry, logbook=logbook, follows=follows)


@entries.route("/", methods=["POST"])
def write_entry():
    data = request.form

    logbook_id = int(data["logbook"])
    logbook = Logbook.get(Logbook.id == logbook_id)

    # a list of attachment filenames
    attachments = data.getlist("attachment")
    print("attachments", attachments)

    # Pick up attributes
    attributes = {}
    for attr in logbook.attributes:
        value = data.get("attribute-{}".format(attr["name"]))
        if value:
            # since we always get strings from the form, we need to
            # convert the values to proper types
            attributes[attr["name"]] = logbook.convert_attribute(
                attr["name"], value)

    # Make a list of authors
    authors = [author.strip()
               for author in data.getlist("author")
               if author]

    entry_id = int(data.get("entry", 0))
    if entry_id:
        # editing an existing entry
        print(entry_id)
        try:
            entry = Entry.get(Entry.id == entry_id)
            change = entry.make_change({
                "title": data["title"],
                "content": data["content"],
                "authors": authors,
                "attributes": attributes,
                "attachments": attachments
            })
            change.save()
        except Exception as e:
            print(e)
    else:
        # creating a new entry
        entry = Entry(title=data["title"],
                      authors=authors,
                      content=data["content"],
                      follows=int(data.get("follows", 0)) or None,
                      attributes=attributes,
                      archived="archived" in data,
                      attachments=attachments,
                      logbook=logbook_id)
    entry.save()

    follows = int(data.get("follows", 0))
    if follows:
        return redirect("#/logbook/{}/entry/{}/{}".format(
            logbook.id, follows, entry.id))
    return redirect("#/logbook/{}/entry/{}".format(logbook.id, entry.id))
