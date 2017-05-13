from datetime import datetime

from flask import request, make_response, jsonify
from flask_restful import Resource, reqparse, marshal, marshal_with, abort
from peewee import DoesNotExist
from playhouse.shortcuts import dict_to_model

from ..db import Entry, Logbook, EntryLock
from ..attachments import handle_img_tags
from ..utils import get_utc_datetime
from . import fields


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
entry_parser.add_argument("follows", type=int, store_missing=False)
entry_parser.add_argument("attributes", type=dict, location="json", default={})
entry_parser.add_argument("archived", type=bool, default=False)
entry_parser.add_argument("metadata", type=dict, location="json", default={})
entry_parser.add_argument("revision_n", type=int, store_missing=False)


class EntryResource(Resource):

    "Handle requests for a single entry"

    @marshal_with(fields.entry_full)
    def get(self, entry_id, logbook_id=None):
        parser = reqparse.RequestParser()
        parser.add_argument("revision", type=int)
        parser.add_argument("acquire_lock", type=bool)
        args = parser.parse_args()
        entry = Entry.get(Entry.id == entry_id)
        try:
            ip = request.remote_addr
            lock = entry.get_lock(ip=ip, acquire=args.get("acquire_lock"))
        except Entry.Locked:
            # a lock is held by someone else
            return entry._thread
        if args["revision"] is not None:
            return entry.get_revision(args["revision"])
        return entry._thread

    @marshal_with(fields.entry_full)
    def post(self, logbook_id):
        "new entry"
        logbook = Logbook.get(Logbook.id == logbook_id)
        data = entry_parser.parse_args()
        # TODO: clean up
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
                converted_value = logbook.convert_attribute(attr_name, attr_value)
                try:
                    if converted_value is not None:
                        attributes[attr_name] = converted_value
                except ValueError:
                    pass
                # TODO: return a helpful error if this fails?
            data["attributes"] = attributes
        entry = dict_to_model(Entry, data)
        entry.save()
        for attachment in inline_attachments:
            attachment.entry = entry
            attachment.save()
        return entry

    @marshal_with(fields.entry_full)
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
                "Conflict: Entry {} has been edited since you last saw it!"
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
entries_parser.add_argument("n", type=int, default=50)
entries_parser.add_argument("offset", type=int, store_missing=False)


class EntriesResource(Resource):

    "Handle requests for entries from a given logbook, optionally filtered"

    @marshal_with(fields.entries)
    def get(self, logbook_id=None):
        args = entries_parser.parse_args()

        attributes = [attr.split(":")
                      for attr in args.get("attributes", [])]

        if logbook_id:
            # restrict search to the given logbook and its descendants
            logbook = Logbook.get(Logbook.id == logbook_id)
            args = dict(child_logbooks=True,
                        title_filter=args.get("title"),
                        content_filter=args.get("content"),
                        author_filter=args.get("authors"),
                        attribute_filter=attributes,
                        n=args["n"], offset=args["offset"])
            entries = logbook.get_entries(**args)
            # TODO: figure out a nicer way to get the total number of hits
            count = logbook.get_entries(count=True, **args).tuples()
            count = list(count)[0][0] if list(count) else 0

        else:
            # global search (all logbooks)
            logbook = None
            args = dict(child_logbooks=True,
                        title_filter=args.get("title"),
                        content_filter=args.get("content"),
                        author_filter=args.get("authors"),
                        attribute_filter=attributes,
                        n=args["n"], offset=args["offset"])
            entries = Entry.search(**args)
            # TODO: figure out a nicer way to get the total number of hits
            count = Entry.search(count=True, **args).tuples()
            count = list(count)[0][0] if list(count) else 0

        return dict(logbook=logbook, entries=list(entries), count=count)


class EntryLockResource(Resource):

    @marshal_with(fields.entry_lock)
    def get(self, entry_id, logbook_id=None):
        "Check for a lock"
        entry = Entry.get(Entry.id == entry_id)
        lock = entry.get_lock(request.remote_addr)
        if lock:
            return lock
        raise EntryLock.DoesNotExist

    @marshal_with(fields.entry_lock)
    def post(self, entry_id, logbook_id=None):
        "Acquire (optionally stealing) a lock"
        parser = reqparse.RequestParser()
        parser.add_argument("steal", type=bool, default=False)
        args = parser.parse_args()
        entry = Entry.get(Entry.id == entry_id)
        print("remote_addr", request.remote_addr)
        return entry.get_lock(ip=request.remote_addr, acquire=True,
                              steal=args["steal"])

    @marshal_with(fields.entry_lock)
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
        lock.cancel(request.remote_addr)
        return lock
