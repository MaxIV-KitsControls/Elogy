from datetime import datetime, timedelta
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

    created_at = DateTimeField(default=datetime.utcnow)
    last_changed_at = DateTimeField(null=True)
    name = CharField()
    description = TextField(null=True)
    parent = ForeignKeyField("self", null=True, related_name="children")
    attributes = JSONField(default=[])
    archived = BooleanField(default=False)

    def get_entries(self, **kwargs):

        "Convenient way to query for entries in this logbook"
        return Entry.search(logbook=self, **kwargs)

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

    def convert_attribute(self, info, value):
        "Try to convert an attribute value to the format the logbook expects"
        # Mainly useful when the logbook configuration may have changed, and
        # trying to access attributes of previously created entries.
        # Not much point in converting them until someone edits the entry.
        if value is None and not info["required"]:
            # ignore unset values if not required
            return
        if info["type"] == "number":
            try:
                return float(value)
            except ValueError:
                return 0
        elif info["type"] == "boolean":
            return bool(value)
        elif info["type"] == "text" and isinstance(value, list):
            return ", ".join(str(item) for item in value)
        elif info["type"] == "multioption" and isinstance(value, str):
            return [value]
        return value

    def get_form_attributes(self, formdata):
        result = {}
        for attribute in self.attributes or []:
            formitem = "attribute-{name}".format(**attribute)
            if attribute["type"] == "multioption":
                # In this case we'll get the data as a list of strings
                value = formdata.getlist(formitem)
            else:
                # in all other cases as a single value
                value = formdata.get(formitem)
            if value:
                result[attribute["name"]] = self.convert_attribute(
                    attribute, value)
        return result


class LogbookRevision(db.Model):
    logbook = ForeignKeyField(Logbook)
    timestamp = DateTimeField(default=datetime.utcnow)
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
    authors = JSONField(default=[])
    content = TextField(null=True)
    content_type = CharField(default="text/html; charset=UTF-8")
    metadata = JSONField(default={})  # general
    attributes = JSONField(default={})
    created_at = DateTimeField(default=datetime.utcnow)
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
            return (Entry.select()
                    .where((Entry.logbook == self.logbook) &
                           (Entry.follows == None) &
                       (Entry.created_at < self.created_at))
                    .order_by(Entry.created_at.desc())
                    .get())
        except DoesNotExist:
            pass

    def make_change(self, **data):
        "Change the entry, storing the old values as a revision"
        original_values = {
            attr: getattr(self, attr)
            for attr, value in data.items()
            if hasattr(self, attr) and getattr(self, attr) != value
        }
        change = EntryRevision(entry=self, **original_values)
        for attr in original_values:
            value = data[attr]
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

    @property
    def lock(self):
        try:
            return EntryLock.get((EntryLock.entry == self) &
                                 (EntryLock.expires_at < datetime.utcnow()))
        except EntryLock.DoesNotExist:
            return False

    @classmethod
    def search(cls, logbook=None, followups=True,
               child_logbooks=False, archived=False,
               n=None, offset=0, count=False,
               attribute_filter=None, content_filter=None,
               title_filter=None, author_filter=None,
               attachment_filter=None):

        # recursive query to get an entire "thread" (starting at 9586)
        # with recursive entry1(id,logbook_id,title,authors,content,content_type,metadata,attributes,tags,created_at,last_changed_at,follows_id,archived) as (select * from entry where id=9586 union all select entry.* from entry,entry1 where entry.follows_id=entry1.id) select * from entry1;

        # Note: this is all a little messy. The reason we're building
        # the query as a raw string is that peewee does not (currently)
        # support recursive queries, which we need in order to search
        # through nested logbooks. This code can probably be cleaned
        # up a bit though.

        if attribute_filter:
            # need to extract the attribute values from JSON here, so that
            # we can match on them later
            attributes = ", {}".format(
                ", ".join(
                    "json_extract(entry.attributes, '$.{attr}') as {attr_id}"
                    .format(attr=attr, attr_id="attr{}".format(i))
                    for i, (attr, _) in enumerate(attribute_filter)))
        else:
            attributes = ""

        if author_filter:
            # extract the authors as a separate table
            authors = ", json_each(entry.authors) as authors"
        else:
            authors = ""

        if logbook:
            if child_logbooks:
                # recursive query to find all entries in the given logbook
                # or any of its descendants, to arbitrary depth
                query = """
with recursive logbook1(id,parent_id) as (
    values({logbook}, null)
    union all
    select logbook.id, logbook.parent_id from logbook,logbook1
    where logbook.parent_id=logbook1.id
)
select {what}{attributes}
from entry{authors}
join logbook1 where entry.logbook_id=logbook1.id
""".format(attributes=attributes,
           what="count()" if count else "entry.*",
           authors=authors, logbook=logbook.id)
            else:
                # this could be done with peewee but since we're doing
                # the rest manually we might as well do this one too
                # since it's trivial.
                query = (
                    "select *{attributes} from entry{authors} where entry.logbook_id = {logbook}"
                    .format(logbook=logbook,
                            attributes=attributes,
                            authors=authors))
        else:
            # same here
            query = ("select *{attributes} from entry{authors} where 1"  # :)
                     .format(attributes=attributes, authors=authors))

        if not archived:
            query += " and not entry.archived"

        # further filters on the results, depending on search criteria
        if content_filter:
            # need to filter out null or REGEX will explode on them
            query += " and entry.content is not NULL and entry.content REGEXP '{}'".format(content_filter)
        if title_filter:
            query += " and entry.title is not NULL and entry.title REGEXP '{}'".format(title_filter)
        if author_filter:
            query += " and authors.value LIKE '{}'".format(author_filter)

        # if attachment_filter:
        #     entries = (
        #         entries
        #         .join(Attachment)
        #         .where(
        #             (~ Attachment.embedded) &
        #             # Here, ** means "case insensitive like" or ILIKE
        #             (Attachment.path ** "%{}%".format(attachment_filter)))
        #         # avoid multiple hits on the same entry
        #         .group_by(Entry.id))

        if attribute_filter:
            for i, (attr, value) in enumerate(attribute_filter):
                # attr_value = fn.json_extract(Entry.attributes, "$." + attr)
                query += " and {} = '{}'".format("attr{}".format(i), value)

        # sort newest first, taking into account the last edit if any
        # TODO: does this make sense? Should we only consider creation date?
        query += " order by coalesce(entry.last_changed_at, entry.created_at) desc"

        if n:
            query += " limit {}".format(n)
            if offset:
                query += " offset {}".format(offset)

        return Entry.raw(query)


DeferredEntry.set_model(Entry)


class EntryRevision(db.Model):
    """Represents a change of an entry.

    Counter-intuitively, what's stored here is the *old* entry
    data. The point is that then we only need to store the fields that
    actually were changed! But it becomes a bit confusing when it's
    time to reconstruct an old entry.
    """
    entry = ForeignKeyField(Entry, related_name="revisions")
    logbook = ForeignKeyField(Logbook, null=True)
    timestamp = DateTimeField(default=datetime.utcnow)
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
    def content_htmldiff(self):
        if self.content:
            new_content = self.get_attribute("content")
            return htmldiff(self.content, new_content)
        return self.get_attribute("content")

    @property
    def current_authors(self):
        if self.authors:
            return self.authors
        return self.get_attribute("authors")

    @property
    def current_title(self):
        if self.title:
            return self.title
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
    created_at = DateTimeField(default=datetime.utcnow)
    lifetime = IntegerField(default=3600)
    owner_ip = CharField()

    @property
    def locked(self):
        return self.created_at + timedelta(seconds=self.lifetime) > datetime.utcnow()


class Attachment(db.Model):
    """Store information about an attachment, e.g. an arbitrary file
    associated with an entry. The file itself is not stored in the
    database though, only a path to where it's expected to be.
    """
    entry = ForeignKeyField(Entry, null=True, related_name="attachments")
    filename = CharField(null=True)
    timestamp = DateTimeField(default=datetime.utcnow)
    path = CharField()  # path within the upload folder
    content_type = CharField(null=True)
    embedded = BooleanField(default=False)  # i.e. an image in the content
    metadata = JSONField(null=True)  # may contain image size, etc
    archived = BooleanField(default=False)

    class Meta:
        order_by = ("id",)
