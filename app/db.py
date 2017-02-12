from datetime import datetime
from html.parser import HTMLParser
import json
from lxml import etree, html
from playhouse.shortcuts import model_to_dict, dict_to_model

from playhouse.flask_utils import FlaskDB
from playhouse.sqlite_ext import JSONField
# from playhouse.sqlite_ext import FTS5Model, SearchField
from peewee import (CharField, TextField, IntegerField, BooleanField,
                    DateTimeField, ForeignKeyField)
from peewee import DoesNotExist, DeferredRelation, fn, JOIN

from .patch import make_patch, apply_patch


db = FlaskDB()  # wrapper, to make config cleaner


class JSONField_(TextField):

    "Stores a JSON string. Encodes/decodes on access"

    def db_value(self, value):
        if value:
            return json.dumps(value)

    def python_value(self, value):
        if value:
            return json.loads(value)
        return {}


def cleanup_html(bad_html):
    "Shape up a HTML string"
    if not bad_html.strip():
        return ""
    tree = html.document_fromstring(bad_html)
    # TODO: some intelligent cleanup here, removing evil tags such as
    # <html>, <body>, <script>, <style>, <iframe>, ...
    # Might also remove stuff like multiple empty <p>
    return '\n'.join(
        (etree.tostring(stree, pretty_print=True, method="xml")
         .decode("utf-8")
         .strip())
        for stree in tree[0].iterchildren()
    )


class HTMLField(TextField):

    "Stores a HTML string. It applies a cleanup step before storing"

    def db_value(self, value):
        if value:
            return cleanup_html(value)


class Logbook(db.Model):

    """
    A logbook is a collection of entries, and (possibly) other logbooks.
    """

    created_at = DateTimeField(default=datetime.now)
    last_changed_at = DateTimeField(null=True)
    name = CharField()
    description = TextField(null=True)
    parent = ForeignKeyField("self", null=True)
    attributes = JSONField(null=True)
    archived = BooleanField(default=False)

    @property
    def children(self):
        # return [model_to_dict(lb, recurse=False)
        #         for lb in Logbook.select().where(Logbook.parent == self)]
        return Logbook.select().where(Logbook.parent == self)

    def get_entries(self, followups=True, attribute_filters=None,
                    archived=False, n=None):
        Followup = Entry.alias()
        entries = (
            Entry.select(
                Entry,
                fn.count(Followup.id).alias("n_followups"),
                Entry.created_at.alias("timestamp"))  # a helpful alias
        )
        if archived:
            entries = (entries
                       .where(Entry.logbook == self.id)
                       .join(Followup, JOIN.LEFT_OUTER,
                             on=(Followup.follows == Entry.id)))
        else:
            entries = (entries
                       .where((Entry.logbook == self.id) &
                              ~Entry.archived)
                       .join(Followup, JOIN.LEFT_OUTER,
                             on=((Followup.follows == Entry.id) &
                                 ~Followup.archived)))
        if not followups:
            entries = (entries.where(Entry.follows == None)
                       .group_by(Entry.id)
                       .order_by(fn.coalesce(
                           Followup.created_at,
                           Entry.created_at).desc()))
        else:
            entries = (entries
                       .group_by(Entry.id)
                       # .where(Entry.follows == None)
                       .order_by(Entry.created_at.desc()))

        if attribute_filters:
            for attr, value in attribute_filters.items():
                attr_value = fn.json_extract(Entry.attributes, "$." + attr)
                entries = entries.where(attr_value == value)

        if n:
            return entries.limit(n)
        return entries

    @property
    def ancestors(self):
        "The list of parent, grandparent, ..."
        parents = []
        # TODO: maybe this can be done with a recursive query?
        if self.parent:
            parent = Logbook.get(Logbook == self.parent)
            while True:
                parents.append(parent)
                try:
                    parent = Logbook.get(Logbook == parent.parent)
                except DoesNotExist:
                    break
        return list(reversed(parents))

    def make_change(self, data):
        "Change the logbook, storing the old values as a revision"
        original_values = {
            attr: getattr(self, attr)
            for attr, value in data.items()
            if getattr(self, attr) != value
        }
        change = LogbookRevision(logbook=self, **original_values)
        for attr, value in data.items():
            setattr(self, attr, value)
        self.last_changed_at = change.timestamp
        change.save()
        self.save()
        return change

    @property
    def entry_histogram(self):
        data = (Entry.select(fn.date(Entry.created_at).alias("date"),
                             fn.min(Entry.id).alias("id"),
                             fn.count(Entry.id).alias("count"))
                .group_by(fn.date(Entry.created_at))
                .order_by(fn.date(Entry.created_at)))
        return [(e.date.timestamp(), e.id, e.count) for e in data]

    def convert_attribute(self, name, value):
        attributes = {
            attr["name"]: attr
            for attr in self.attributes
        }
        info = attributes[name]
        if value is None and not info["required"]:
            # ignore unset values if not required
            return
        if info["type"] == "number":
            return float(value)
        elif info["type"] == "boolean":
            return bool(value)
        else:  # string or option
            return value


class LogbookRevision(db.Model):
    logbook = ForeignKeyField(Logbook)
    timestamp = DateTimeField(default=datetime.now)
    name = CharField(null=True)
    description = TextField(null=True)
    attributes = JSONField(null=True)
    archived = BooleanField(null=True)
    parent_id = IntegerField(null=True)


DeferredEntry = DeferredRelation()


# class EntrySearch(FTS5Model):
#     entry = ForeignKeyField(DeferredEntry)
#     content = SearchField()


class MLStripper(HTMLParser):

    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


class Entry(db.Model):

    logbook = ForeignKeyField(Logbook, related_name="entries")
    title = CharField(null=True)
    authors = JSONField(null=True)
    content = HTMLField(null=True)
    content_type = CharField(default="text/html; charset=UTF-8")  # TODO: should not default to HTML
    metadata = JSONField(null=True)  # general
    attributes = JSONField(null=True)
    tags = JSONField(null=True)
    created_at = DateTimeField(default=datetime.now)
    last_changed_at = DateTimeField(null=True)
    follows = ForeignKeyField("self", null=True)
    archived = BooleanField(default=False)

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     if "content" in kwargs:
    #         EntrySearch(entry=self,
    #                     content=strip_tags(kwargs["content"])).save()

    class Meta:
        order_by = ("-created_at",)

    @property
    def followups(self):
        return [entry for entry in
                (Entry.select()
                 .where(Entry.follows_id == self.id)
                 .order_by(Entry.id))]

    @property
    def next(self):
        "Next entry (order by id)"
        try:
            return (Entry.select()
                    .where((Entry.logbook == self.logbook) &
                           (Entry.follows == None) &
                           (Entry.created_at > self.created_at))
                    .order_by(Entry.created_at)
                    .get())
        except DoesNotExist:
            pass

    @property
    def previous(self):
        "Previous entry (order by id)"
        try:
            return model_to_dict(
                Entry.select()
                .where((Entry.logbook == self.logbook) &
                       (Entry.follows == None) &
                       (Entry.created_at < self.created_at))
                .order_by(Entry.created_at.desc())
                .get(), recurse=False)
        except DoesNotExist:
            pass

    def make_change(self, **data):
        "Change the entry, storing the old values as a revision"
        original_values = {
            attr: getattr(self, attr)
            for attr, value in data.items()
            if getattr(self, attr) != value
        }
        if "content" in data:
            content = cleanup_html(data["content"])
            diff = make_patch(content, self.content)
            original_values["content"] = diff
        change = EntryRevision(entry=self, **original_values)
        for attr, value in data.items():
            setattr(self, attr, value)
        self.last_changed_at = change.timestamp
        return change

    def get_old_version(self, change_id):
        pass

    @property
    def stripped_content(self):
        return strip_tags(self.content)

    def get_attachments(self, embedded=False):
        return self.attachments.filter(Attachment.embedded == embedded)


DeferredEntry.set_model(Entry)


class EntryRevision(db.Model):
    "Represents a change of an entry"
    entry = ForeignKeyField(Entry, related_name="revisions")
    logbook = ForeignKeyField(Logbook, null=True)
    timestamp = DateTimeField(default=datetime.now)
    title = CharField(null=True)
    authors = JSONField(null=True)
    content = TextField(null=True)
    metadata = JSONField(null=True)
    attributes = JSONField(null=True)
    follows_id = IntegerField(null=True)
    tags = JSONField(null=True)
    archived = BooleanField(default=False)

    revision_authors = JSONField(null=True)
    revision_comment = TextField(null=True)


class EntryLock(db.Model):
    "Contains temporary edit locks, to prevent overwriting changes"
    entry = ForeignKeyField(Entry)
    timestamp = DateTimeField(default=datetime.now)
    owner_ip = CharField()


class Attachment(db.Model):
    "Store information about an attachment"
    entry = ForeignKeyField(Entry, null=True, related_name="attachments")
    timestamp = DateTimeField(default=datetime.now)
    path = CharField()  # path within the upload folder
    content_type = CharField(null=True)
    embedded = BooleanField(default=False)  # i.e. an image in the content
    metadata = JSONField(null=True)  # may contain image size, etc

    class Meta:
        order_by = ("id",)
