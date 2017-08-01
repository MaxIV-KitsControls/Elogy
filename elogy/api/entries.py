from datetime import datetime
import logging

from flask import request, send_file, abort
from flask_restful import Resource, reqparse, marshal, marshal_with, abort

from ..db import Entry, Logbook, EntryLock
from ..attachments import handle_img_tags
from ..export import export_entries_as_pdf
from ..actions import new_entry, edit_entry
from ..utils import get_utc_datetime
from . import fields, send_signal


entry_parser = reqparse.RequestParser()
entry_parser.add_argument("id", type=int, store_missing=False)
entry_parser.add_argument("title", type=str, store_missing=False)
entry_parser.add_argument("content", type=str, store_missing=False)
entry_parser.add_argument("content_type", type=str, default="text/html",
                          store_missing=False)
entry_parser.add_argument("authors", type=dict, action="append",
                          store_missing=False)
entry_parser.add_argument("created_at", type=str, store_missing=False)
entry_parser.add_argument("last_changed_at", type=str, store_missing=False)
entry_parser.add_argument("follows_id", type=int, store_missing=False)
entry_parser.add_argument("attributes", type=dict, location="json", default={})
entry_parser.add_argument("archived", type=bool, default=False)
entry_parser.add_argument("metadata", type=dict, location="json", default={})
entry_parser.add_argument("priority", type=int, default=0)
entry_parser.add_argument("revision_n", type=int, store_missing=False)


class EntryResource(Resource):

    "Handle requests for a single entry"

    @marshal_with(fields.entry_full, envelope="entry")
    def get(self, entry_id, logbook_id=None, revision_n=None):
        parser = reqparse.RequestParser()
        parser.add_argument("thread", type=bool)
        args = parser.parse_args()
        entry = Entry.get(Entry.id == entry_id)
        if revision_n is not None:
            return entry.get_revision(revision_n)
        if args.thread:
            return entry._thread
        return entry

    @send_signal(new_entry)
    @marshal_with(fields.entry_full, envelope="entry")
    def post(self, logbook_id, entry_id=None):
        "Creating a new entry"
        logbook = Logbook.get(Logbook.id == logbook_id)
        data = entry_parser.parse_args()
        # TODO: clean up
        if entry_id is not None:
            # In this case, we're creating a followup to an existing entry
            data["follows"] = entry_id
        if "created_at" in data:
            data["created_at"] = get_utc_datetime(data["created_at"])
        else:
            data["created_at"] = datetime.utcnow()
        if "last_changed_at" in data:
            data["last_changed_at"] = get_utc_datetime(data["last_changed_at"])
        if data.get("content"):
            content_type = data.get("content_type", "text/html")
            if content_type.startswith("text/html"):
                data["content"], inline_attachments = handle_img_tags(
                    data["content"], timestamp=data["created_at"])
            else:
                inline_attachments = []
        else:
            inline_attachments = []
        data["logbook"] = logbook
        # make sure the attributes are of proper types
        if "attributes" in data:
            attributes = {}
            for attr_name, attr_value in data["attributes"].items():
                try:
                    converted_value = logbook.convert_attribute(attr_name,
                                                                attr_value)
                    attributes[attr_name] = converted_value
                except ValueError as e:
                    logging.warning(
                        "Discarding attribute %s with value %r; %s",
                        attr_name, attr_value, e)
                    pass
                # TODO: return a helpful error if this fails?
            data["attributes"] = attributes
        entry = Entry.create(**data)
        for attachment in inline_attachments:
            attachment.entry = entry
            attachment.save()
        return entry

    @send_signal(edit_entry)
    @marshal_with(fields.entry_full, envelope="entry")
    def put(self, entry_id, logbook_id=None):
        "update entry"
        args = entry_parser.parse_args()
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


# parser for validating query arguments to the entries resource
entries_parser = reqparse.RequestParser()
entries_parser.add_argument("title", type=str)
entries_parser.add_argument("content", type=str)
entries_parser.add_argument("authors", type=str)
entries_parser.add_argument("attachments", type=str)
entries_parser.add_argument("attribute", type=str,
                            dest="attributes",
                            action="append", default=[])
entries_parser.add_argument("archived", type=bool)
entries_parser.add_argument("ignore_children", type=bool, default=False)
entries_parser.add_argument("n", type=int, default=50)
entries_parser.add_argument("offset", type=int, store_missing=False)
entries_parser.add_argument("download", type=str, store_missing=False)


class EntriesResource(Resource):

    "Handle requests for entries from a given logbook, optionally filtered"

    def get(self, logbook_id=None):
        args = entries_parser.parse_args()

        attributes = [attr.split(":")
                      for attr in args.get("attributes", [])]

        if logbook_id:
            # restrict search to the given logbook and its descendants
            logbook = Logbook.get(Logbook.id == logbook_id)
            search_args = dict(child_logbooks=not args.get("ignore_children"),
                               title_filter=args.get("title"),
                               content_filter=args.get("content"),
                               author_filter=args.get("authors"),
                               attachment_filter=args.get("attachments"),
                               attribute_filter=attributes,
                               n=args["n"], offset=args.get("offset"))
            entries = logbook.get_entries(**search_args)
            # TODO: figure out a nicer way to get the total number of hits
            count = logbook.get_entries(count=True, **search_args).tuples()
            count = list(count)[0][0] if list(count) else 0

        else:
            # global search (all logbooks)
            logbook = None
            search_args = dict(child_logbooks=not args.get("ignore_children"),
                               title_filter=args.get("title"),
                               content_filter=args.get("content"),
                               author_filter=args.get("authors"),
                               attachment_filter=args.get("attachments"),
                               attribute_filter=attributes,
                               n=args["n"], offset=args.get("offset"))
            entries = Entry.search(**search_args)
            # TODO: figure out a nicer way to get the total number of hits
            count = Entry.search(count=True, **search_args).tuples()
            count = list(count)[0][0] if list(count) else 0

        if args.get("download") == "pdf":
            # return a PDF version
            # TODO: not sure if this belongs in the API
            pdf = export_entries_as_pdf(logbook, entries)
            if pdf is None:
                abort(400)
            return send_file(pdf, mimetype="application/pdf",
                             as_attachment=True,
                             attachment_filename=("{logbook.name}.pdf"
                                                  .format(logbook=logbook)))

        return marshal(dict(logbook=logbook,
                            entries=list(entries), count=count), fields.entries)


class EntryLockResource(Resource):

    @marshal_with(fields.entry_lock, envelope="lock")
    def get(self, entry_id, logbook_id=None):
        "Check for a lock"
        entry = Entry.get(Entry.id == entry_id)
        lock = entry.get_lock(request.environ["REMOTE_ADDR"])
        if lock:
            return lock
        raise EntryLock.DoesNotExist

    @marshal_with(fields.entry_lock, envelope="lock")
    def post(self, entry_id, logbook_id=None):
        "Acquire (optionally stealing) a lock"
        parser = reqparse.RequestParser()
        parser.add_argument("steal", type=bool, default=False)
        args = parser.parse_args()
        entry = Entry.get(Entry.id == entry_id)
        print("remote_addr", request.environ.get("REMOTE_ADDR"))
        return entry.get_lock(ip=request.environ["REMOTE_ADDR"],
                              acquire=True,
                              steal=args["steal"])

    @marshal_with(fields.entry_lock, envelope="lock")
    def delete(self, entry_id=None, logbook_id=None):
        "Cancel a lock"
        parser = reqparse.RequestParser()
        parser.add_argument("lock_id", type=int, store_missing=False)
        args = parser.parse_args()
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
