from datetime import datetime
from html.parser import HTMLParser
from playhouse.shortcuts import model_to_dict, dict_to_model

from playhouse.flask_utils import FlaskDB
from playhouse.sqlite_ext import JSONField
# from playhouse.sqlite_ext import FTS5Model, SearchField
from peewee import (CharField, TextField, IntegerField, BooleanField,
                    DateTimeField, ForeignKeyField)
from peewee import DoesNotExist, DeferredRelation, fn, JOIN

from .patch import make_patch, apply_patch
from .htmldiff import htmldiff


db = FlaskDB()  # wrapper, to make config cleaner


class Logbook(db.Model):

    """
    A logbook is a collection of entries, and (possibly) other logbooks.
    """

    created_at = DateTimeField(default=datetime.now)
    last_changed_at = DateTimeField(null=True)
    name = CharField()
    description = TextField(null=True)
    parent = ForeignKeyField("self", null=True, related_name="children")
    attributes = JSONField(null=True)
    archived = BooleanField(default=False)

    def get_entries(self, followups=True, attribute_filters=None,
                    child_logbooks=False, archived=False, n=None):

        "Convenient way to query for entries in this logbook"

        # build a suitable query
        Followup = Entry.alias()
        entries = (
            Entry.select(
                Entry,
                fn.count(Followup.id).alias("n_followups"),
                Entry.created_at.alias("timestamp"))  # a helpful alias
        )
        # we can include entries from logbooks that are contained in this one
        if child_logbooks:
            # TODO: we only get immediate children here, no grandchildren
            # and so on. Figure out a way to do that!
            entries = (entries.join(Logbook, JOIN.LEFT_OUTER)
                       .where((Logbook.id == self.id) |
                              (Logbook.parent == self)))
        else:
            entries = entries.where(Entry.logbook == self.id)

        # Entries marked as "archived" should normally not be included
        if archived:
            entries = (entries
                       .join(Followup, JOIN.LEFT_OUTER,
                             on=(Followup.follows == Entry.id)))
        else:
            entries = (entries
                       .where(~Entry.archived)
                       .join(Followup, JOIN.LEFT_OUTER,
                             on=((Followup.follows == Entry.id) &
                                 ~Followup.archived)))

        # 'followups' are entries that relate to an earlier entry
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

        # filter on attribute values
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
    content = TextField(null=True)
    content_type = CharField(default="text/html; charset=UTF-8")  # TODO: should not default to HTML
    metadata = JSONField(null=True)  # general
    attributes = JSONField(null=True)
    tags = JSONField(null=True)
    created_at = DateTimeField(default=datetime.now)
    last_changed_at = DateTimeField(null=True)
    follows = ForeignKeyField("self", null=True, related_name="followups")
    archived = BooleanField(default=False)

    class Meta:
        order_by = ("created_at",)

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
        change = EntryRevision(entry=self, **original_values)
        for attr, value in data.items():
            setattr(self, attr, value)
        self.last_changed_at = change.timestamp
        return change

    def get_old_version(self, revision_id):
        revisions = (EntryRevision.select()
                     .where(EntryRevision.entry == self
                            and EntryRevision.id >= revision_id)
                     .order_by(EntryRevision.id.desc()))
        content = self.content
        print(content)
        print("---")
        for revision in revisions:
            print(revision.content)
            if revision.content:
                content = apply_patch(content, revision.content)
        return content

    @property
    def stripped_content(self):
        return strip_tags(self.content)

    def get_attachments(self, embedded=False):
        return self.attachments.filter((Attachment.embedded == embedded) &
                                       ~Attachment.archived)


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

    @property
    def content_htmldiff(self):
        if self.content:
            #old_content = self.entry.get_old_version(self.id)
            new_content = self.get_attribute("content")
            print(self.content, new_content)
            return htmldiff(self.content, new_content)
        return self.get_attribute("content")

    def get_attribute(self, attr):
        try:
            return getattr(
                EntryRevision.select()
                .where((EntryRevision.entry == self.entry) &
                       (getattr(EntryRevision, attr) != None) &
                       (EntryRevision.id > self.id))
                .order_by(EntryRevision.id)
                .get(), attr)
        except DoesNotExist:
            return getattr(self.entry, attr)

    @property
    def current_authors(self):
        return self.get_attribute("authors")

    @property
    def current_title(self):
        return self.get_attribute("title")

    @property
    def new_title(self):
        return self.get_attribute("title")

    @property
    def new_authors(self):
        return self.get_attribute("authors")

    @property
    def prev_version(self):
        index = list(self.entry.revisions).index(self)
        if index > 0:
            return index - 1

    @property
    def next_version(self):
        revisions = list(self.entry.revisions)
        index = revisions.index(self)
        if index < (len(revisions) - 1):
            return index + 1

    
class EntryLock(db.Model):
    "Contains temporary edit locks, to prevent overwriting changes"
    entry = ForeignKeyField(Entry)
    timestamp = DateTimeField(default=datetime.now)
    owner_ip = CharField()


class Attachment(db.Model):
    "Store information about an attachment"
    entry = ForeignKeyField(Entry, null=True, related_name="attachments")
    filename = CharField(null=True)
    timestamp = DateTimeField(default=datetime.now)
    path = CharField()  # path within the upload folder
    content_type = CharField(null=True)
    embedded = BooleanField(default=False)  # i.e. an image in the content
    metadata = JSONField(null=True)  # may contain image size, etc
    archived = BooleanField(default=False)

    class Meta:
        order_by = ("id",)
