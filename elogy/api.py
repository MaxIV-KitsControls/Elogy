import pwd, grp

from dateutil.parser import parse
from datetime import datetime
from flask import request, jsonify, url_for
from flask_restful import Resource, reqparse, fields, marshal, marshal_with
import lxml
from playhouse.shortcuts import dict_to_model
from werkzeug import FileStorage

from .db import Logbook, LogbookRevision, Entry, EntryRevision
from .attachments import save_attachment, handle_img_tags
from .utils import get_utc_datetime


class NumberOfSomething(fields.Raw):
    def format(self, value):
        return len(value)


logbook_child_fields = {
    "id": fields.Integer,
    "name": fields.String,
    "description": fields.String,
    "n_children": NumberOfSomething(attribute="children")
}


short_logbook_fields = {
    "id": fields.Integer,
    "name": fields.String,
}


attribute_fields = {
    "type": fields.String,
    "name": fields.String,
    "required": fields.Boolean,
    "options": fields.List(fields.String)
}


logbook_fields = {
    "id": fields.Integer,
    "name": fields.String,
    "description": fields.String,
    "parent": fields.Nested(short_logbook_fields),
    "created_at": fields.String,
    "children": fields.List(fields.Nested(logbook_child_fields)),
    "attributes": fields.List(fields.Nested(attribute_fields))
}


logbooks_parser = reqparse.RequestParser()
logbooks_parser.add_argument("parent", type=int)
logbooks_parser.add_argument("name", type=str, required=True)
logbooks_parser.add_argument("description", type=str)
logbooks_parser.add_argument("attributes", type=list,
                             location="json", default=[])
logbooks_parser.add_argument("archived", type=bool, default=False)


class LogbooksResource(Resource):

    "Handle requests for logbooks"

    @marshal_with(logbook_fields)
    def get(self, logbook_id=None):

        if logbook_id:
            print("logbook_id", logbook_id)
            result = Logbook.get(Logbook.id == logbook_id)
            print(result)
            return result

        # Get either the direct children of a given parent, or else the
        # global list of top-level (no parent) logbooks
        parser = reqparse.RequestParser()
        parser.add_argument("parent", type=int)
        args = parser.parse_args()
        parent_id = args.get("parent")
        if parent_id:
            return Logbook.get(Logbook.id == parent_id)
        else:
            children = (Logbook.select()
                        .where(Logbook.parent == None))
            return dict(children=children)

    def post(self):
        "Create a new logbook"
        args = logbooks_parser.parse_args()
        print(args)
        logbook = dict_to_model(Logbook, args)
        logbook.save()
        return jsonify(logbook_id=logbook.id)

    def put(self, logbook_id):
        "Update an existing logbook"
        logbook = Logbook.get(Logbook.id == logbook_id)
        change = logbook.make_change(request.json)
        logbook.save()
        change.save()
        return jsonify(revision_id=change.id)


def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']


# parser for validating query arguments to the entries resource
entries_parser = reqparse.RequestParser()
entries_parser.add_argument("title", type=str)
entries_parser.add_argument("content", type=str)
entries_parser.add_argument("authors", type=str)
entries_parser.add_argument("attachments", type=str)
entries_parser.add_argument("attributes", type=str)
entries_parser.add_argument("archived", type=bool)
entries_parser.add_argument("n", type=int, default=50)
entries_parser.add_argument("offset", type=int, default=0)


attachment_fields = {
    "path": fields.String,
    "filename": fields.String,
    "embedded": fields.Boolean,
    "content_type": fields.String,
    "metadata": fields.Raw
}


class Followup(fields.Raw):
    "Since followups can contain followups, and so on, we need this"
    def format(self, value):
        return marshal(value, followup_fields)


followup_fields = {
    "id": fields.Integer,
    "title": fields.String,
    "created_at": fields.DateTime,
    "authors": fields.List(fields.String),
    "attachments": fields.List(fields.Nested(attachment_fields)),
    "attributes": fields.Raw,
    "content": fields.String,
    "content_type": fields.String,
    "followups": fields.List(Followup),
}


class EntryId(fields.Raw):
    def format(self, value):
        print(value)
        return value.id if value else None


entry_lock_fields = {
    "expires_at": fields.DateTime,
    "owner_ip": fields.String
}

entry_fields = {
    "id": fields.Integer,
    "logbook": fields.Nested(logbook_fields),
    "title": fields.String,
    "created_at": fields.DateTime,
    "last_changed_at": fields.DateTime,
    "authors": fields.List(fields.String),
    "attributes": fields.Raw,
    "attachments": fields.List(fields.Nested(attachment_fields)),
    "content": fields.String,
    "content_type": fields.String,
    "follows": EntryId,
    "n_followups": NumberOfSomething(attribute="followups"),
    "followups": fields.List(Followup),
    "lock": fields.Nested(entry_lock_fields),
    "next": EntryId,
    "previous": EntryId
}


entry_parser = reqparse.RequestParser()
entry_parser.add_argument("id", type=int, store_missing=False)
# entry_parser.add_argument("logbook_id", type=int)
entry_parser.add_argument("title", type=str, store_missing=False)
entry_parser.add_argument("content", type=str, store_missing=False)
entry_parser.add_argument("content_type", type=str, default="text/html", store_missing=False)
entry_parser.add_argument("authors", type=str, action="append", store_missing=False)
entry_parser.add_argument("created_at", type=str, store_missing=False)
entry_parser.add_argument("last_changed_at", type=str, store_missing=False)
entry_parser.add_argument("follows", type=int, store_missing=False)
# entry_parser.add_argument("attachments", type=list, location="json")
entry_parser.add_argument("attributes", type=dict, location="json", store_missing=False)
entry_parser.add_argument("archived", type=bool, default=False, store_missing=False)
entry_parser.add_argument("metadata", type=dict, location="json", store_missing=False)


class EntryResource(Resource):

    "Handle requests for a single entry"

    @marshal_with(entry_fields)
    def get(self, entry_id, logbook_id=None):
        return Entry.get(Entry.id == entry_id)

    def post(self, logbook_id=None):
        "new entry"
        data = entry_parser.parse_args()
        logbook_id = logbook_id or data["logbook_id"]
        if "created_at" in data:
            data["created_at"] = get_utc_datetime(data["created_at"])
        else:
            data["created_at"] = datetime.utcnow()
        if "last_changed_at" in data:
            data["last_changed_at"] = get_utc_datetime(data["last_changed_at"])
        data["content"], inline_attachments = handle_img_tags(
            data.get("content", ""), timestamp=data["created_at"])
        logbook = Logbook.get(Logbook.id == logbook_id)
        data["logbook"] = logbook
        entry = dict_to_model(Entry, data)
        entry.save()
        for attachment in inline_attachments:
            attachment.entry = entry
            attachment.save()
        return jsonify(entry_id=entry.id)

    def put(self, logbook_id=None, entry_id=None):
        "update entry"
        print(request.json)
        args = entry_parser.parse_args()
        entry_id = entry_id or args["id"]
        args["content"], inline_attachments = handle_img_tags(args["content"])
        entry = Entry.get(Entry.id == entry_id)
        change = entry.make_change(**args)
        entry.save()
        change.save()
        for attachment in inline_attachments:
            attachment.entry = entry
            attachment.save()
        return jsonify(revision_id=change.id)


class FirstIfAny(fields.Raw):
    def format(self, value):
        if value:
            return marshal(value[0], attachment_fields)


class ContentPreview(fields.Raw):
    def format(self, value):
        value = value.strip()
        if value:
            document = lxml.html.document_fromstring(value)
            raw_text = document.text_content()
            return raw_text[:200].strip().replace("\n", " ")


short_entry_fields = {
    "id": fields.Integer,
    "logbook": fields.Nested(short_logbook_fields),
    "title": fields.String,
    "content": ContentPreview,
    "created_at": fields.DateTime,
    "last_changed_at": fields.DateTime,
    "authors": fields.List(fields.String),
    "attributes": fields.Raw,
    # "attachments": fields.List(fields.Nested(attachment_fields)),
    "attachment_preview": FirstIfAny(attribute="attachments"),
    "n_attachments": NumberOfSomething(attribute="attachments"),
    "n_followups": NumberOfSomething(attribute="followups"),
}


entries_fields = {
    "logbook": fields.Nested(logbook_fields),
    "entries": fields.List(fields.Nested(short_entry_fields)),
    "count": fields.Integer
}


class EntriesResource(Resource):

    "Handle requests for entries from a given logbook, optionally filtered"

    @marshal_with(entries_fields)
    def get(self, logbook_id=None):
        args = entries_parser.parse_args()

        if args.get("attributes"):
            attributes = [attr.split(":")
                          for attr in args.get("attributes", "").split(",")]
        else:
            attributes = None

        if logbook_id:
            # restrict search to the given logbook and its descendants
            logbook = Logbook.get(Logbook.id == logbook_id)
            entries = logbook.get_entries(child_logbooks=True,
                                          title_filter=args.get("title"),
                                          content_filter=args.get("content"),
                                          author_filter=args.get("authors"),
                                          attribute_filter=attributes,
                                          n=args["n"], offset=args["offset"])
            # TODO: figure out a nicer way to get the total number of hits
            count = logbook.get_entries(child_logbooks=True, count=True,
                                        title_filter=args.get("title"),
                                        content_filter=args.get("content"),
                                        author_filter=args.get("authors"),
                                        attribute_filter=attributes,
                                        n=args["n"], offset=args["offset"]).tuples()
            count = list(count)[0][0] if list(count) else 0

        else:
            # global search (all logbooks)
            logbook = None
            entries = Entry.search(child_logbooks=True,
                                   title_filter=args.get("title"),
                                   content_filter=args.get("content"),
                                   author_filter=args.get("authors"),
                                   attribute_filter=attributes,
                                   n=args["n"], offset=args["offset"])
            # TODO: figure out a nicer way to get the total number of hits
            count = Entry.search(child_logbooks=True, count=True,
                                 title_filter=args.get("title"),
                                 content_filter=args.get("content"),
                                 author_filter=args.get("authors"),
                                 attribute_filter=attributes,
                                 n=args["n"], offset=args["offset"]).tuples()
            count = list(count)[0][0] if list(count) else 0

        return dict(logbook=logbook, entries=list(entries), count=count)


users_parser = reqparse.RequestParser()
users_parser.add_argument("search", type=str, default="")


class UsersResource(Resource):

    """
    Note: The list of users is just taken from the underlying
    system. Elogy does not really know or care where users come from,
    it just stores the authors as a list of arbitrary strings. This
    is intended as a convenient way to find user names.
    """

    def get(self, username=None):
        args = users_parser.parse_args()
        search_string = args.get("search", "")
        candidates = []
        for entry in pwd.getpwall():
            full_name = entry.pw_gecos.strip(" ,")
            if (entry.pw_name.startswith(search_string) or
                search_string in full_name.lower()):
                candidates.append({
                    "login": entry.pw_name,
                    "name": full_name
                })
        return jsonify(users=candidates)


attachments_parser = reqparse.RequestParser()
attachments_parser.add_argument("entry_id", type=int, required=True)
attachments_parser.add_argument(
    "attachment", type=FileStorage, action="append",
    location='files', required=True)
attachments_parser.add_argument("timestamp", type=str)
attachments_parser.add_argument("embedded", type=bool, default=False)


class AttachmentsResource(Resource):

    def post(self):
        "Upload attachments to an entry"
        args = attachments_parser.parse_args()
        if args["timestamp"]:
            timestamp = get_utc_datetime(args["timestamp"])
        else:
            timestamp = datetime.utcnow()
        for attachment in args["attachment"]:
            print(attachment.filename)
            attachment = save_attachment(attachment, timestamp,
                                         args["entry_id"],
                                         embedded=args["embedded"])
            attachment.save()
        return jsonify(location=url_for("get_attachment",
                                        path=attachment.path),
                       content_type=attachment.content_type,
                       filename=attachment.filename,
                       metadata=attachment.metadata)
