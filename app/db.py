from datetime import datetime
from html.parser import HTMLParser
import json
from lxml import etree
from playhouse.shortcuts import model_to_dict, dict_to_model

from playhouse.flask_utils import FlaskDB
from playhouse.sqlite_ext import FTS5Model, SearchField
from peewee import (CharField, TextField, IntegerField, BooleanField,
                    DateTimeField, ForeignKeyField)
from peewee import DoesNotExist, DeferredRelation, fn, JOIN
from bs4 import BeautifulSoup

from .patch import make_patch, apply_patch

db = FlaskDB()  # wrapper, to make config cleaner


class JSONField(TextField):

    "Stores a JSON string. Encodes/decodes on access"

    def db_value(self, value):
        if value:
            return json.dumps(value)

    def python_value(self, value):
        if value:
            return json.loads(value)
        return {}


def cleanup_html_(bad_html):
    if not bad_html.strip():
        return ""
    tree = etree.HTML(bad_html.replace('\r', ''))
    return '\n'.join(
        (etree.tostring(stree, pretty_print=True, method="xml")
         .decode("utf-8")
         .strip())
        for stree in tree[0].iterchildren()
    )


def cleanup_html(bad_html):
    tree = BeautifulSoup(bad_html)
    return tree.prettify()


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
    description = TextField()
    parent = ForeignKeyField("self", null=True)
    attributes = JSONField(null=True)
    archived = BooleanField(default=False)

    # class Meta:
    #     order_by = fn.coalesce('-last_changed_at', '-created_at')

    @property
    def children(self):
        return [model_to_dict(lb, recurse=False)
                for lb in Logbook.select().where(Logbook.parent == self)]

    def get_entries_(self, followups=False,
                    page=None, entries_per_page=None):
        entries = (Entry.select()
                   .where(Entry.logbook == self)
                   .order_by(fn.coalesce(Entry.last_changed_at,
                                         Entry.created_at).desc()))
        if not followups:
            entries = entries.where(Entry.follows == None)
        if page is not None and entries_per_page is not None:
            entries = entries.paginate(page, entries_per_page)
        return entries

    def get_entries(self, archived=False, n=10):
        Followup = Entry.alias()
        entries = (
            Entry.select(
                Entry,
                fn.count(Followup.id).alias("n_followups"),
                fn.coalesce(Followup.last_changed_at,
                            Followup.created_at,
                            Entry.last_changed_at,
                            Entry.created_at)
                .alias("timestamp"))  # a helpful alias
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
        entries = (entries
                   .where(Entry.follows == None)
                   .group_by(Entry.id)
                   # Sort newest first, where the latest followup is
                   # preferred, and edits bumps the timestamps.
                   # Note that editing an entry will *not* cause
                   # it to be sorted as newer than its newest followup
                   # (if any). Not sure if this makes sense...
                   .order_by(
                       fn.coalesce(Followup.last_changed_at,
                                   Followup.created_at,
                                   Entry.last_changed_at,
                                   Entry.created_at)
                       .desc()
                   )
        )
        return entries.limit(n)

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


class EntrySearch(FTS5Model):
    entry = ForeignKeyField(DeferredEntry)
    content = SearchField()


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
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
    title = CharField()
    authors = CharField()
    content = HTMLField()
    attributes = JSONField(null=True)
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

    # @property
    # def timestamp(self):
    #     return self.last_changed_at or self.created_at

    @property
    def next(self):
        "Next entry (order by id)"
        try:
            return model_to_dict(
                Entry.select()
                .where((Entry.logbook == self.logbook) &
                       (Entry.follows == None) &
                       (Entry.id > self.id))
                .order_by(Entry.id)
                .get(), recurse=False)
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
                       (Entry.id < self.id))
                .order_by(Entry.id.desc())
                .get(), recurse=False)
        except DoesNotExist:
            pass

    def make_change(self, data):
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
        change.save()
        self.save()
        return change

    def get_old_version(self, change_id):
        pass


DeferredEntry.set_model(Entry)


class EntryRevision(db.Model):
    "Represents a change of an entry"
    entry = ForeignKeyField(Entry, related_name="revisions")
    logbook = ForeignKeyField(Logbook, null=True)
    timestamp = DateTimeField(default=datetime.now)
    title = CharField(null=True)
    authors = CharField(null=True)
    content = TextField(null=True)
    attributes = JSONField(null=True)
    follows_id = IntegerField(null=True)
    archived = BooleanField(default=False)
