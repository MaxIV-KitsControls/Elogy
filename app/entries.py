from base64 import decodestring
from datetime import datetime
import io
import json
from jinja2 import TemplateNotFound

from bs4 import BeautifulSoup
from .db import Entry, Logbook
from flask import (Blueprint, abort, redirect, render_template, request,
                   url_for)
from werkzeug import FileStorage
from peewee import JOIN, fn, DoesNotExist
from lxml import html

from .attachments import save_attachment


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


def handle_img_tags(text, timestamp):
    soup = BeautifulSoup(text)
    attachments = []
    for img in soup.findAll('img'):
        src = img['src']
        if src.startswith("data:"):
            header, data = src[5:].split(",", 1)
            filetype, encoding = header.split(";")
            try:
                filename = "decoded." + filetype.split("/")[1].lower()
            except IndexError:
                print("weird filetype!?", filetype)
                continue
            file_ = FileStorage(io.BytesIO(decodestring(data.encode("ascii"))),
                                filename=filename)
            src = img["src"] = save_attachment(file_, timestamp)

        attachments.append(src)
    return str(soup), attachments


@entries.route("/", methods=["POST"])
def write_entry():
    data = request.form

    logbook_id = int(data["logbook"])
    logbook = Logbook.get(Logbook.id == logbook_id)

    # a list of attachment filenames
    attachments = data.getlist("attachment")
    try:
        # Grab all image elements from the HTML.
        # TODO: this will explode on data URIs, those should
        # be ignored. Also we need to ignore links to external images.
        #tree = html.document_fromstring(data.get("content"))
        #attachments = tree.xpath('//img/@src')
        content, attachments = handle_img_tags(data.get("content"), datetime.now())
    except SyntaxError as e:
        print(e)
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
        return redirect("/entries/{}#{}".format(follows, entry.id))
    return redirect("/entries/{}".format(entry.id))
