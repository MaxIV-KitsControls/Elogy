import time
from datetime import datetime

from flask import request, make_response, jsonify
from flask_restful import Resource, reqparse, marshal, marshal_with
from playhouse.shortcuts import dict_to_model

from ..db import Entry, Logbook, EntryLock
from ..attachments import handle_img_tags
from ..utils import get_utc_datetime
from . import fields


entry_parser = reqparse.RequestParser()
entry_parser.add_argument("id", type=int, store_missing=False)
# entry_parser.add_argument("logbook_id", type=int)
entry_parser.add_argument("title", type=str, store_missing=False)
entry_parser.add_argument("content", type=str, store_missing=False)
entry_parser.add_argument("content_type", type=str, default="text/html",
                          store_missing=False)
entry_parser.add_argument("authors", type=dict, action="append",
                          store_missing=False)
entry_parser.add_argument("created_at", type=str, store_missing=False)
entry_parser.add_argument("last_changed_at", type=str, store_missing=False)
entry_parser.add_argument("follows", type=int, store_missing=False)
# entry_parser.add_argument("attachments", type=list, location="json")
entry_parser.add_argument("attributes", type=dict, location="json", default={})
entry_parser.add_argument("archived", type=bool, default=False)
entry_parser.add_argument("metadata", type=dict, location="json", default={})
entry_parser.add_argument("acquire_lock", type=bool, location="args",
                          store_missing=False)


class EntryResource(Resource):

    "Handle requests for a single entry"

    def get(self, entry_id=None, logbook_id=None):
        args = entry_parser.parse_args()
        entry = Entry.get(Entry.id == entry_id)
        try:
            ip = request.remote_addr if args.get("acquire_lock") else None
            lock = entry.get_lock(ip=ip, acquire=True)
        except Entry.Locked:
            # a lock is held by someone else
            return dict(entry=marshal(entry._thread, fields.entry_full))
        if not lock:
            return dict(entry=marshal(entry._thread, fields.entry_full))
        return dict(entry=marshal(entry._thread, fields.entry_full),
                    lock=marshal(lock, fields.entry_lock))

    def post(self, logbook_id):
        "new entry"
        logbook = Logbook.get(Logbook.id == logbook_id)
        data = entry_parser.parse_args()
        if "created_at" in data:
            data["created_at"] = get_utc_datetime(data["created_at"])
        else:
            data["created_at"] = datetime.utcnow()
        if "last_changed_at" in data:
            data["last_changed_at"] = get_utc_datetime(data["last_changed_at"])
        data["content"], inline_attachments = handle_img_tags(
            data.get("content", ""), timestamp=data["created_at"])
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
        return jsonify(entry_id=entry.id)

    def put(self, entry_id, logbook_id=None, lock_id=None):
        "update entry"
        args = entry_parser.parse_args()
        entry_id = entry_id or args["id"]
        entry = Entry.get(Entry.id == entry_id)
        # check for a lock on the entry
        if lock_id:
            # the user has the lock ID, that's good enough
            try:
                lock = Lock.get(Lock.id == lock_id)
                lock.cancel(request.remote_addr)
            except DoesNotExist:
                pass
        else:
            try:
                lock = entry.get_lock(ip=request.remote_addr)
                # the lock is no longer needed
                lock.cancel(request.remote_addr)
            except Entry.Locked:
                result = dict(
                    message=(
                        "Conflict: Entry {} is locked by IP {} since {                        .format(entry_id, lock.owner_ip, lock.created_at)),
                )
                return make_response(jsonify(result), 409)

        args["content"], inline_attachments = handle_img_tags(args["content"])
        entry = Entry.get(Entry.id == entry_id)
        change = entry.make_change(**args)
        entry.save()
        change.save()
        for attachment in inline_attachments:
            attachment.entry = entry
            attachment.save()
        return jsonify(revision_id=change.id)


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
entries_parser.add_argument("offset", type=int, default=0)


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
