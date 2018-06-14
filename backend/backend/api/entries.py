import logging

from flask import request, send_file
from flask_restful import Resource, marshal, marshal_with, abort
from webargs.fields import (Integer, Str, Boolean, Dict, List,
                            Nested, Email, LocalDateTime)
from webargs.flaskparser import use_args

from ..db import Entry, Logbook, EntryLock
from ..attachments import handle_img_tags
from ..export import export_entries_as_pdf
from ..actions import new_entry, edit_entry
from . import fields, send_signal


entry_args = {
    "id": Integer(allow_none=True),
    "logbook_id": Integer(allow_none=True),
    "title": Str(allow_none=True),
    "content": Str(),
    "content_type": Str(missing="text/html"),
    "authors": List(Nested({
        "name": Str(),
        "login": Str(allow_none=True),
        "email": Email(allow_none=True)
    }), validate=lambda a: len(a) > 0),
    "created_at": LocalDateTime(),
    "last_changed_at": LocalDateTime(allow_none=True),
    "follows_id": Integer(allow_none=True),
    "attributes": Dict(),
    "archived": Boolean(),
    "no_change_time": Boolean(),
    "metadata": Dict(),
    "priority": Integer(missing=0),
    "revision_n": Integer(),
}


class EntryResource(Resource):

    "Handle requests for a single entry"

    @use_args({"thread": Boolean(missing=False)})
    @marshal_with(fields.entry_full, envelope="entry")
    def get(self, args, entry_id, logbook_id=None, revision_n=None):
        entry = Entry.get(Entry.id == entry_id)
        if revision_n is not None:
            return entry.get_revision(revision_n)
        if args["thread"]:
            return entry._thread
        return entry

    @send_signal(new_entry)
    @use_args(entry_args)
    @marshal_with(fields.entry_full, envelope="entry")
    def post(self, args, logbook_id, entry_id=None):
        "Creating a new entry"
        logbook = Logbook.get(Logbook.id == logbook_id)
        # TODO: clean up
        if entry_id is not None:
            # we're creating a followup to an existing entry
            args["follows"] = entry_id
        if args.get("content"):
            content_type = args["content_type"]
            if content_type.startswith("text/html"):
                # extract any inline images as attachments
                args["content"], inline_attachments = handle_img_tags(
                    args["content"], timestamp=args.get("created_at"))
            else:
                inline_attachments = []
        else:
            inline_attachments = []
        args["logbook"] = logbook
        # make sure the attributes are of proper types
        try:
            args["attributes"] = logbook.check_attributes(args.get("attributes", {}))
        except ValueError as e:
            abort(422, messages={"attributes": [str(e)]})
        if args.get("follows_id"):
            # don't allow pinning followups, that makes no sense
            args["pinned"] = False
        entry = Entry.create(**args)
        for attachment in inline_attachments:
            attachment.entry = entry
            attachment.save()
        return entry

    @send_signal(edit_entry)
    @use_args(entry_args)
    @marshal_with(fields.entry_full, envelope="entry")
    def put(self, args, entry_id, logbook_id=None):
        "update entry"
        entry_id = entry_id or args["id"]
        entry = Entry.get(Entry.id == entry_id)
        # to prevent overwiting someone else's changes we require the
        # client to supply the "revision_n" field of the entry they
        # are editing. If this does not match the current entry in the
        # db, it means someone has changed it inbetween and we abort.
        if "revision_n" not in args:
            abort(400, message="Missing 'revision_n' field!")
        if args["revision_n"] != entry.revision_n:
            abort(409, message=(
                "Conflict: Entry {} has been edited since you last loaded it!"
                .format(entry_id)))
        # check for a lock on the entry
        if entry.lock:
            if entry.lock.owned_by_ip == request.remote_addr:
                entry.lock.cancel(request.remote_addr)
            else:
                abort(409, message=(
                    "Conflict: Entry {} is locked by IP {} since {}"
                    .format(entry_id, entry.lock.owned_by_ip,
                            entry.lock.created_at)))
        if args.get("content"):
            content_type = args.get("content_type", entry.content_type)
            if content_type.startswith("text/html"):
                args["content"], inline_attachments = handle_img_tags(
                    args["content"])
            else:
                inline_attachments = []
        else:
            inline_attachments = []

        entry = Entry.get(Entry.id == entry_id)
        change = entry.make_change(**args)
        entry.save()
        change.save()
        for attachment in inline_attachments:
            attachment.entry = entry
            attachment.save()
        return entry


entries_args = {
    "title": Str(),
    "content": Str(),
    "authors": Str(),
    "attachments": Str(),
    "attribute": List(Str(validate=lambda s: len(s.split(":")) == 2)),
    "metadata": List(Str(validate=lambda s: len(s.split(":")) == 2)),
    "archived": Boolean(),
    "ignore_children": Boolean(),
    "n": Integer(missing=50),
    "offset": Integer(),
    "download": Boolean(),
    "sort_by_timestamp": Boolean(missing=True),
}


class EntriesResource(Resource):

    "Handle requests for entries from a given logbook, optionally filtered"

    @use_args(entries_args)
    def get(self, args, logbook_id=None):

        attributes = [attr.split(":")
                      for attr in args.get("attribute", [])]
        metadata = [meta.split(":")
                    for meta in args.get("metadata", [])]

        if logbook_id:
            # restrict search to the given logbook and its descendants
            logbook = Logbook.get(Logbook.id == logbook_id)
            search_args = dict(child_logbooks=not args.get("ignore_children"),
                               title_filter=args.get("title"),
                               content_filter=args.get("content"),
                               author_filter=args.get("authors"),
                               attachment_filter=args.get("attachments"),
                               attribute_filter=attributes,
                               metadata_filter=metadata,
                               n=args["n"], offset=args.get("offset"),
                               sort_by_timestamp=args.get("sort_by_timestamp"))
            entries = logbook.get_entries(**search_args)
        else:
            # global search (all logbooks)
            logbook = None
            search_args = dict(child_logbooks=not args.get("ignore_children"),
                               title_filter=args.get("title"),
                               content_filter=args.get("content"),
                               author_filter=args.get("authors"),
                               attachment_filter=args.get("attachments"),
                               attribute_filter=attributes,
                               metadata_filter=metadata,
                               n=args["n"], offset=args.get("offset"),
                               sort_by_timestamp=args.get("sort_by_timestamp"))
            entries = Entry.search(**search_args)

        if args.get("download") == "pdf":
            # return a PDF version
            # TODO: not sure if this belongs in the API
            pdf = export_entries_as_pdf(logbook, entries)
            if pdf is None:
                abort(400, message="Could not create PDF!")
            return send_file(pdf, mimetype="application/pdf",
                             as_attachment=True,
                             attachment_filename=("{logbook.name}.pdf"
                                                  .format(logbook=logbook)))

        return marshal(dict(logbook=logbook,
                            entries=list(entries)), fields.entries)


class EntryLockResource(Resource):

    @marshal_with(fields.entry_lock, envelope="lock")
    def get(self, entry_id, logbook_id=None):
        "Check for a lock"
        entry = Entry.get(Entry.id == entry_id)
        lock = entry.get_lock(request.environ["REMOTE_ADDR"])
        if lock:
            return lock
        raise EntryLock.DoesNotExist

    @use_args({"steal": Boolean(missing=False)})
    @marshal_with(fields.entry_lock, envelope="lock")
    def post(self, args, entry_id, logbook_id=None):
        "Acquire (optionally stealing) a lock"
        entry = Entry.get(Entry.id == entry_id)
        return entry.get_lock(ip=request.environ["REMOTE_ADDR"],
                              acquire=True,
                              steal=args["steal"])

    @use_args({"lock_id": Integer()})
    @marshal_with(fields.entry_lock, envelope="lock")
    def delete(self, args, entry_id=None, logbook_id=None):
        "Cancel a lock"
        if "lock_id" in args:
            lock = EntryLock.get(EntryLock.id == args["lock_id"])
        else:
            entry = Entry.get(Entry.id == entry_id)
            lock = entry.get_lock()
        lock.cancel(request.environ["REMOTE_ADDR"])
        return lock


class EntryChangesResource(Resource):

    @marshal_with(fields.entry_changes)
    def get(self, entry_id, logbook_id=None):
        entry = Entry.get(Entry.id == entry_id)
        return {"entry_changes": entry.changes}
