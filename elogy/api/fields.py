from collections import OrderedDict
from dateutil.parser import parse
import json

from flask_restful import fields, marshal, marshal_with_field
import lxml


class NumberOf(fields.Raw):
    def format(self, value):
        return len(value)


logbook_child = {
    "id": fields.Integer,
    "name": fields.String,
    "description": fields.String,
    "n_children": NumberOf(attribute="children")
}


attribute = {
    "type": fields.String,
    "name": fields.String,
    "required": fields.Boolean,
    "options": fields.List(fields.String)
}


class LogbookField(fields.Raw):
    "Helper for returning nested logbooks"
    def format(self, value):
        return marshal(value, logbook)


class NonArchivedList(fields.List):
    "Filter out archived items from the given list"
    def format(self, value):
        items = []
        for item in value:
            if not item.archived:
                items.append(item)
        return super().format(items)


logbook_short = {
    "id": fields.Integer,
    "parent_id": fields.Integer(attribute="parent.id"),
    "name": fields.String,
    "description": fields.String,
    "children": NonArchivedList(LogbookField),
}


logbook = {
    "id": fields.Integer,
    "name": fields.String,
    "description": fields.String,
    "template": fields.String,
    "parent": fields.Nested({
        "id": fields.Integer(default=None),
        "name": fields.String
    }, allow_null=True),
    "created_at": fields.String,
    "children": NonArchivedList(LogbookField),
    "attributes": fields.List(fields.Nested(attribute)),
    "metadata": fields.Raw,
    "archived": fields.Boolean
}


authors = {
    "name": fields.String,
    "login": fields.String,
    "email": fields.String
}


logbookchange_metadata = {
    "id": fields.Integer,
    "timestamp": fields.DateTime,
    "change_authors": fields.List(fields.Nested(authors)),
    "change_comment": fields.String,
    "chante_ip": fields.String,
}


class LogbookChangeField(fields.Raw):
    def format(self, change):
        change_fields = {
            field: dict(old=change.get_old_value(field),
                        new=change.get_new_value(field))
            for field in ["name", "description", "template", "attributes"]
            if field in change.changed
        }
        meta_fields = marshal(change, logbookchange_metadata)
        return {
            "changed": change_fields,
            **meta_fields
        }


logbook_changes = {
    "logbook_changes": fields.List(LogbookChangeField)
}


attachment = {
    "id": fields.Integer,
    "filename": fields.String,
    "embedded": fields.Boolean,
    "timestamp": fields.DateTime,
    "content_type": fields.String,
    "metadata": fields.Raw,
    "link": fields.String,
    "thumbnail_link": fields.String
}


class Followup(fields.Raw):
    "Since followups can contain followups, and so on, we need this"
    def format(self, value):
        return marshal(value, followup)


class EntryId(fields.Raw):
    def format(self, value):
        return value.id if value else None


entry_lock = {
    "id": fields.Integer,
    "created_at": fields.DateTime,
    "expires_at": fields.DateTime,
    "owned_by_ip": fields.String,
    "cancelled_at": fields.DateTime,
    "cancelled_by_ip": fields.String
}


# followups don't need to contain e.g. logbook information since we
# can assume that they belong to the same logbook as their parent
followup = {
    "id": fields.Integer,
    "title": fields.String,
    "created_at": fields.DateTime,
    "last_changed_at": fields.DateTime,
    "authors": fields.List(fields.Nested(authors)),
    "attachments": fields.List(fields.Nested(attachment)),
    "attributes": fields.Raw,
    "content": fields.String,
    "content_type": fields.String,
    "n_followups": NumberOf(attribute="followups"),
    "followups": NonArchivedList(Followup),
    "metadata": fields.Raw,
    "revision_n": fields.Integer,
    "lock": fields.Nested(entry_lock, allow_null=True),
}

entry_full = {
    "id": fields.Integer,
    "logbook": fields.Nested(logbook),
    "title": fields.String,
    "created_at": fields.DateTime,
    "last_changed_at": fields.DateTime,
    "authors": fields.List(fields.Nested(authors)),
    "attributes": fields.Raw(attribute="converted_attributes"),
    "attachments": fields.List(fields.Nested(attachment)),
    "priority": fields.Integer,
    "metadata": fields.Raw,
    "content": fields.String,
    "content_type": fields.String,
    "follows": EntryId,
    "n_followups": NumberOf(attribute="followups"),
    "followups": NonArchivedList(Followup),
    "revision_n": fields.Integer,
    "lock": fields.Nested(entry_lock, allow_null=True),
    "next": EntryId,
    "previous": EntryId,
    "archived": fields.Boolean
}

entry = {
    "entry": fields.Nested(entry_full),
    "lock": fields.Nested(entry_lock, default=None)
}


entrychange_metadata = {
    "id": fields.Integer,
    "timestamp": fields.DateTime,
    "change_authors": fields.List(fields.Nested(authors)),
    "change_comment": fields.String,
    "change_ip": fields.String,
}


class EntryChangeField(fields.Raw):
    def format(self, change):
        change_fields = {
            field: dict(old=change.get_old_value(field),
                        new=change.get_new_value(field))
            for field in ["title", "content", "authors", "attributes"]
            if field in change.changed
        }
        meta_fields = marshal(change, entrychange_metadata)
        return {
            "changed": change_fields,
            **meta_fields
        }


entry_changes = {
    "entry_changes": fields.List(EntryChangeField)
}


class FirstIfAny(fields.Raw):
    def format(self, value):
        if value:
            return marshal(value[0], attachment)


class ContentPreview(fields.Raw):
    def format(self, value):
        value = value.strip()
        if value:
            document = lxml.html.document_fromstring(value)
            raw_text = document.text_content()
            return raw_text[:200].strip().replace("\n", " ")


class DateTimeFromStringField(fields.DateTime):
    def format(self, value):
        return super().format(parse(value))


logbook_very_short = {
    "id": fields.Integer,
    "name": fields.String,
}


class FollowupAuthorsField(fields.Raw):
    def format(self, value):
        all_authors = sum(json.loads(value), [])
        d = OrderedDict((author["name"], None) for author in all_authors)
        return list(d.keys())


short_entry = {
    "id": fields.Integer,
    "logbook": fields.Nested(logbook_very_short),
    "title": fields.String,
    "content": ContentPreview,
    "priority": fields.Integer,
    "created_at": fields.DateTime,
    "last_changed_at": fields.DateTime,
    "timestamp": DateTimeFromStringField,
    "authors": fields.List(fields.String(attribute="name")),
    "attributes": fields.Raw,
    "followup_authors": FollowupAuthorsField(),
    "attachment_preview": FirstIfAny(attribute="attachments"),
    "n_attachments": NumberOf(attribute="attachments"),
    "n_followups": fields.Integer
}


entries = {
    "logbook": fields.Nested(logbook),
    "entries": fields.List(fields.Nested(short_entry)),
}


user = {
    "login": fields.String,
    "name": fields.String,
    "email": fields.String
}
