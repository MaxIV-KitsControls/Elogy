"""
Blueprint that handles stuff related to individual entries; displaying,
creating, editing etc.
"""

from base64 import decodestring
import binascii
from datetime import datetime
import io
import os

from dateutil.parser import parse
from flask import (Blueprint, redirect, render_template, request,
                   url_for, jsonify, current_app)
from werkzeug import FileStorage
from peewee import DoesNotExist
from lxml import html, etree
from lxml.html.clean import Cleaner

from .attachments import save_attachment
from .db import Entry, EntryRevision, Logbook, EntryLock, Attachment
from . import actions
from .utils import request_wants_json


entries = Blueprint('entries', __name__)


html_clean = Cleaner(style=True, inline_style=False)


def cleanup_html(bad_html):
    "Shape up a HTML string"
    if not bad_html.strip():
        return ""
    tree = html.document_fromstring(bad_html)
    html_clean(tree)
    # TODO: some intelligent cleanup here, removing evil tags such as
    # <html>, <body>, <script>, <style>, <iframe>, ...
    # Might also remove stuff like multiple empty <p>
    return '\n'.join(
        (etree
         .tostring(stree, pretty_print=True, method="xml")
         .decode("utf-8")
         .strip())
        for stree in tree[0].iterchildren()
    )


@entries.route("/<int:entry_id>")
def show_entry(entry_id):
    "Display an entry"
    entry = Entry.get(Entry.id == entry_id)
    return render_template("entry.jinja2", entry=entry, **request.args)


@entries.route("/<int:entry_id>/<int:version>")
def show_entry_revision(entry_id, version):
    "Display an old revision of an entry"
    entry = Entry.get(Entry.id == entry_id)
    revision = entry.revisions[version-1]
    return render_template("entry_revision.jinja2", entry=entry,
                           revision=revision, **request.args)


@entries.route("/<int:entry_id>/history")
def show_entry_history(entry_id):
    entry = Entry.get(Entry.id == entry_id)
    # revision = EntryRevision.get(EntryRevision.entry == entry)
    return render_template("entry_history.jinja2", entry=entry)


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
    return render_template('edit_entry.jinja2',
                           logbook=logbook, follows=follows)


@entries.route("/edit/<int:entry_id>")
def edit_entry(entry_id):

    "Deliver a form for editing an existing entry"

    entry = Entry.get(Entry.id == entry_id)

    # we use a simple table to store temporary "locks" on entries that
    # are being edited.  The idea is to prevent collisions where one
    # user saves over the edits of another. Note that since all
    # changes are stored, we should never actually *lose* data, but it
    # can still be annoying.
    try:
        lock = EntryLock.get(EntryLock.entry == entry)
        if lock.owner_ip != request.remote_addr:
            return render_template("entry_lock.jinja2", lock=lock)
    except EntryLock.DoesNotExist:
        lock = EntryLock.create(entry=entry, owner_ip=request.remote_addr)

    if entry.follows:
        follows = Entry.get(Entry.id == entry.follows)
    else:
        follows = 0
    logbook = entry.logbook
    return render_template('edit_entry.jinja2',
                           entry=entry, logbook=logbook, follows=follows)


def decode_base64(data):
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    missing_padding = len(data) % 4
    if missing_padding != 0:
        data += b'=' * (4 - missing_padding)
    return decodestring(data)


def handle_img_tags(text, entry_id=None, timestamp=None):
    """Get image tags from the text. Extract embedded images and save
    them as attachments"""
    attachments = []
    timestamp = timestamp or datetime.now()
    try:
        doc = html.document_fromstring(text)
    except etree.ParserError:
        return text, attachments
    for i, element in enumerate(doc.xpath("//*[@src]")):
        src = element.attrib['src'].split("?", 1)[0]
        if src.startswith("data:"):
            header, data = src[5:].split(",", 1)  # TODO: find a safer way
            filetype, encoding = header.split(";")
            try:
                raw_image = decode_base64(data.encode("ascii"))
            except binascii.Error as e:
                print("failed to decode image!", e)
                continue
            try:
                # TODO: possible to be more clever about the filename?
                filename = "decoded-{}-{}.{}".format(
                    len(raw_image), i, filetype.split("/")[1].lower())
            except IndexError:
                print("weird filetype!?", filetype)
                continue
            file_ = FileStorage(io.BytesIO(raw_image),
                                filename=filename, content_type=filetype)
            attachment = save_attachment(file_, timestamp, entry_id,
                                         embedded=True)
            # TODO: maybe it would be a better idea to use a URL like
            # "/attachments/<id>" here, and then just have a redirect
            # to the real URI? That way we could change the way the files
            # are stored under the hood without bothering about having
            # to keep URLs unchanged...
            src = element.attrib["src"] = os.path.join(
                url_for("attachments.get_attachment", filename=""),
                attachment.path)
            if element.getparent().tag == "a":
                element.getparent().attrib["href"] = src

        attachments.append(src)
    return html.tostring(doc), attachments


def remove_lock(entry_id):
    lock = EntryLock.get(EntryLock.entry_id == entry_id)
    lock.delete_instance()


@entries.route("/unlock/<int:entry_id>")
def unlock_entry(entry_id):
    "Remove the lock on the given entry"
    remove_lock(entry_id)
    return redirect(url_for(".show_entry", entry_id=entry_id))


@entries.route("/", methods=["POST"])
@entries.route("/<int:entry_id>", methods=["POST"])
def write_entry(entry_id=None):

    "Save a submitted entry (new or edited)"

    if request.form:
        # This means that the user is posting through a form,
        # presumably via the normal web frontend
        data = request.form

        logbook_id = int(data["logbook"])
        logbook = Logbook.get(Logbook.id == logbook_id)

        # Pick up attributes
        attributes = {}
        for attr in logbook.attributes or []:
            value = data.get("attribute-{}".format(attr["name"]))
            if value:
                # since we always get strings from the form, we need to
                # convert the values to proper types
                attributes[attr["name"]] = logbook.convert_attribute(
                    attr["name"], value)
        # a list of attachment filenames
        attachments = data.getlist("attachment")
        tags = [t.strip() for t in data.getlist("tag")] or None

        # Make a list of authors
        authors = [author.strip()
                   for author in data.getlist("author")
                   if author]
        metadata = None
        content_type = "text/html"
        if content_type == "text/html":
            content = cleanup_html(data.get("content"))
        else:
            content = data.get("content")
        created_at = datetime.now()
        last_changed_at = None
    else:
        # Assuming that the user is posting via the API
        data = request.json
        logbook_id = data["logbook"]
        logbook = Logbook.get(Logbook.id == logbook_id)
        # TODO: check the types of the attributes against the
        # logbook configuration
        attributes = data.get("attributes")
        tags = data.get("tags")
        metadata = data.get("metadata")
        attachments = data.get("attachments", [])
        authors = data.get("authors", [])
        content_type = data.get("content-type", "text/html")
        if content_type == "text/html":
            content = cleanup_html(data.get("content"))
        else:
            content = data.get("content")
        created_at = parse(data.get("created_at"), datetime.now())
        last_changed_at = parse(data.get("last_changed_at"), None)

    new = False
    if entry_id:  # editing an existing entry, first check for locks
        try:
            lock = EntryLock.get(EntryLock.entry_id == entry_id)
            if lock.owner_ip == request.remote_addr:
                # it's our lock
                lock.delete_instance()
            else:
                unlock = int(data.get("unlock", 0))
                if lock.entry_id == unlock:
                    # the user has decided to unlock the entry and save anyway
                    remove_lock(lock.entry_id)
                else:
                    # Locked by someone else. Let's send the user back to
                    # the edit page, everything filled in as it was, with
                    # a warning message.
                    entry = Entry(id=entry_id,
                                  title=data.get("title"),
                                  authors=authors,
                                  content=content,
                                  content_type=content_type,
                                  follows=int(data.get("follows", 0)) or None,
                                  metadata=metadata,
                                  attributes=attributes,
                                  archived="archived" in data,
                                  tags=tags,
                                  logbook=logbook)
                    return render_template("edit_entry.jinja2",
                                           entry=entry, lock=lock)
        except DoesNotExist as e:
            # No lock!
            pass

        # Now make the change
        entry = Entry.get(Entry.id == entry_id)
        change = entry.make_change(title=data.get("title"),
                                   content=content,
                                   content_type=content_type,
                                   authors=authors,
                                   metadata=metadata,
                                   attributes=attributes,
                                   tags=tags)
        change.save()
    else:  # creating a new entry
        if content_type == "text/html":
            content = cleanup_html(data.get("content"))
        else:
            content = data.get("content")

        entry = Entry(title=data.get("title"),
                      authors=authors,
                      created_at=created_at,
                      last_changed_at=last_changed_at,
                      content=content,
                      content_type=content_type,
                      follows=int(data.get("follows", 0)) or None,
                      metadata=metadata,
                      attributes=attributes,
                      tags=tags,
                      archived="archived" in data,
                      logbook=logbook)
        new = True

    # TODO: Refactor this; in order to save the attachments we need
    # the entry_id, which means that, if the entry is new, we have to
    # save the entry before fully processing the attachments. A bit
    # of a hen-and-egg problem...

    try:
        # Grab all image elements from the HTML.
        # TODO: this will explode on data URIs, those should
        # be ignored. Also we need to ignore links to external images.
        content, embedded_attachments = handle_img_tags(
            entry.content, entry_id)
        entry.content = cleanup_html(content)
        entry.save()
        for url in embedded_attachments:
            path = url[1:].split("/", 1)[-1]
            try:
                attachment = Attachment.get(Attachment.path == path)
                attachment.entry_id = entry.id
                attachment.save()
            except DoesNotExist:
                print("Did not find attachment", url)
    except SyntaxError as e:
        print(e)

    entry.save()


    # perform actions
    app = current_app._get_current_object()
    if new:
        actions.new_entry.send(app, entry=entry)
    else:
        actions.edit_entry.send(app, entry=entry)

    if request_wants_json():
        return jsonify(entry_id=entry.id)

    follows = int(data.get("follows", 0))
    query = "?new={}".format(entry.id) if new else ""
    if follows:
        return redirect("/entries/{}{}#{}".format(follows, query, entry.id))
    return redirect("/entries/{}{}".format(entry.id, query))
