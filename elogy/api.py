import pwd, grp

from datetime import datetime
from flask import jsonify, url_for
from flask_restful import Resource, reqparse, fields, marshal, marshal_with
import lxml
from playhouse.shortcuts import dict_to_model
from werkzeug import FileStorage

from .db import Logbook, Entry
from .attachments import save_attachment, handle_img_tags
from .utils import get_utc_datetime


# Catch exceptions raised in API endpoints and translate them
# into useful error messages.
# Note: the Flask debugger will catch the exceptions before this.
errors = {
    "LogbookDoesNotExist": dict(
        message="Logbook does not exist!",
        status=404
    ),
    "EntryDoesNotExist": dict(
        message="Entry does not exist!",
        status=404
    ),
    "GroupDoesNotExist": dict(
        message="Group does not exist!",
        status=404
    )
}


class NumberOf(fields.Raw):
    def format(self, value):
        return len(value)


logbook_child_fields = {
    "id": fields.Integer,
    "name": fields.String,
    "description": fields.String,
    "n_children": NumberOf(attribute="children")
}


attribute_fields = {
    "type": fields.String,
    "name": fields.String,
    "required": fields.Boolean,
    "options": fields.List(fields.String)
}


class LogbookField(fields.Raw):
    "Helper for returning nested logbooks"
    def format(self, value):
        return marshal(value, logbook_short_fields)


logbook_short_fields = {
    "id": fields.Integer,
    "parent_id": fields.Integer(attribute="parent.id"),
    "name": fields.String,
    "description": fields.String,
    "children": fields.List(LogbookField),
}


logbook_fields = {
    "id": fields.Integer,
    "name": fields.String,
    "description": fields.String,
    "template": fields.String,
    "parent": fields.Nested({
        "id": fields.Integer(default=None),
        "name": fields.String
    }),
    "created_at": fields.String,
    "children": fields.List(LogbookField),
    "attributes": fields.List(fields.Nested(attribute_fields)),
    "metadata": fields.Raw
}


logbooks_parser = reqparse.RequestParser()
logbooks_parser.add_argument("parent", type=int)
logbooks_parser.add_argument("name", type=str, required=True)
logbooks_parser.add_argument("description", type=str)
logbooks_parser.add_argument("template", type=str)
logbooks_parser.add_argument("attributes", type=list,
                             location="json", default=[])
logbooks_parser.add_argument("metadata", type=dict, location="json",
                             default={})
logbooks_parser.add_argument("archived", type=bool, default=False)


class LogbooksResource(Resource):

    "Handle requests for logbooks"

    @marshal_with(logbook_fields, envelope="logbook")
    def get(self, logbook_id=None):

        if logbook_id:
            return Logbook.get(Logbook.id == logbook_id)

        # Get either the direct children of a given parent, or else the
        # global list of top-level (no parent) logbooks
        parser = reqparse.RequestParser()
        parser.add_argument("parent", type=int)
        args = parser.parse_args()
        parent_id = args.get("parent")
        if parent_id:
            return Logbook.get(Logbook.id == parent_id)
        children = (Logbook.select()
                    .where(Logbook.parent == None))
        return dict(children=children)

    def post(self):
        "Create a new logbook"
        args = logbooks_parser.parse_args()
        logbook = dict_to_model(Logbook, args)
        logbook.save()
        return jsonify(logbook_id=logbook.id)

    def put(self, logbook_id):
        "Update an existing logbook"
        logbook = Logbook.get(Logbook.id == logbook_id)
        args = logbooks_parser.parse_args()
        change = logbook.make_change(args)
        logbook.save()
        change.save()
        return jsonify(revision_id=change.id)


attachment_fields = {
    "path": fields.String,
    "filename": fields.String,
    "embedded": fields.Boolean,
    "content_type": fields.String,
    "metadata": fields.Raw
}


authors_fields = {
    "name": fields.String,
    "login": fields.String
}


class Followup(fields.Raw):
    "Since followups can contain followups, and so on, we need this"
    def format(self, value):
        return marshal(value, followup_fields)


# followups don't need to contain e.g. logbook information since we
# can assume that they belong to the same logbook as their parent
followup_fields = {
    "id": fields.Integer,
    "title": fields.String,
    "created_at": fields.DateTime,
    "authors": fields.List(fields.Nested(authors_fields)),
    "attachments": fields.List(fields.Nested(attachment_fields)),
    "attributes": fields.Raw,
    "content": fields.String,
    "content_type": fields.String,
    "followups": fields.List(Followup),
}


class EntryId(fields.Raw):
    def format(self, value):
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
    "authors": fields.List(fields.Nested(authors_fields)),
    "attributes": fields.Raw(attribute="converted_attributes"),
    "attachments": fields.List(fields.Nested(attachment_fields)),
    "content": fields.String,
    "content_type": fields.String,
    "follows": EntryId,
    "n_followups": NumberOf(attribute="followups"),
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


class EntryResource(Resource):

    "Handle requests for a single entry"

    @marshal_with(entry_fields, envelope="entry")
    def get(self, entry_id, logbook_id=None):
        return Entry.get(Entry.id == entry_id)

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

    def put(self, logbook_id=None, entry_id=None):
        "update entry"
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


logbook_very_short_fields = {
    "id": fields.Integer,
    "name": fields.String,
}

short_entry_fields = {
    "id": fields.Integer,
    "logbook": fields.Nested(logbook_very_short_fields),
    "title": fields.String,
    "content": ContentPreview,
    "created_at": fields.DateTime,
    "last_changed_at": fields.DateTime,
    "authors": fields.List(fields.String(attribute="name")),
    # "attributes": fields.Raw(attribute="converted_attributes"),
    # "attachments": fields.List(fields.Nested(attachment_fields)),
    "attachment_preview": FirstIfAny(attribute="attachments"),
    "n_attachments": NumberOf(attribute="attachments"),
    "n_followups": NumberOf(attribute="followups"),
}


entries_fields = {
    "logbook": fields.Nested(logbook_fields),
    "entries": fields.List(fields.Nested(short_entry_fields)),
    "count": fields.Integer
}


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

    @marshal_with(entries_fields)
    def get(self, logbook_id=None):
        args = entries_parser.parse_args()

        attributes = [attr.split(":")
                      for attr in args.get("attributes", [])]

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
users_parser.add_argument("groups", type=str, default="")


class GroupDoesNotExist(Exception):
    pass


class UsersResource(Resource):

    """
    Note: The list of users is just taken from the underlying
    system. Elogy does not really know or care where users come from,
    it just stores the authors as a list of arbitrary strings. This
    is intended as a convenient way to find user names.

    search: arbitrary string that will be matched against logins and
            full names
    groups: a list of group names to restrict the search to.
    """

    def get(self):
        args = users_parser.parse_args()
        search = args.get("search", "")
        groups = args.get("groups", [])
        if groups:
            groups = groups.split(",")
        candidates = []
        try:
            grp_filter = [grp.getgrnam(group) for group in groups]
        except KeyError:
            raise GroupDoesNotExist
        gids = [g.gr_gid for g in grp_filter]
        # This is a little fiddly; in order to get all users from
        # the given groups we need to both theck if the user has
        # the group as "primary group", or if the user is otherwise
        # a member.
        users = set(u for u in pwd.getpwall()
                    if gids and u.pw_gid in gids or
                    all(u.pw_name in g.gr_mem for g in grp_filter))
        for u in users:
            full_name = u.pw_gecos.strip(" ,")
            if (u.pw_name.startswith(search) or search in full_name.lower()):
                candidates.append({
                    "login": u.pw_name, "name": full_name
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
            attachment = save_attachment(attachment, timestamp,
                                         args["entry_id"],
                                         embedded=args["embedded"])
            attachment.save()
        return jsonify(location=url_for("get_attachment",
                                        path=attachment.path),
                       content_type=attachment.content_type,
                       filename=attachment.filename,
                       metadata=attachment.metadata)
