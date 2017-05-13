from datetime import datetime, timedelta
from functools import wraps
from html.parser import HTMLParser
from playhouse.shortcuts import model_to_dict, dict_to_model

from playhouse.flask_utils import FlaskDB
from playhouse.sqlite_ext import JSONField
from playhouse.signals import Model, post_save, pre_save
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
    template = TextField(null=True)
    template_content_type = CharField(default="text/html; charset=UTF-8")
    parent = ForeignKeyField("self", null=True, related_name="children")
    attributes = JSONField(default=[])
    metadata = JSONField(default={})
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
        change = LogbookRevision.create(logbook=self, **original_values)
        for attr, value in data.items():
            setattr(self, attr, value)
        self.last_changed_at = change.timestamp
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
        "Try to convert an attribute value to the format the logbook expects"
        # Mainly useful when the logbook configuration may have changed, and
        # trying to access attributes of previously created entries.
        # Not much point in converting them until someone edits the entry.
        # Note: does not exert itself to convert values and will raise
        # ValueError if it fails.
        try:
            for info in self.attributes:
                if info["name"] == name:
                    break
            else:
                raise KeyError("Unknown attribute %s!" % name)
            if value is None and not info.get("required"):
                # ignore unset values if not required
                return
            if info["type"] == "text":
                return str(value)
            if info["type"] == "number":
                return float(value)
            elif info["type"] == "boolean":
                # Hmm... this will almost always be True
                return bool(value)
            elif info["type"] == "text" and isinstance(value, list):
                return value[0]
            elif info["type"] == "multioption" and isinstance(value, str):
                return [value]
        except (ValueError, KeyError, IndexError) as e:
            raise ValueError(e)
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

    class Locked(Exception):
        pass

    @property
    def _thread(self):
        entries = []
        if self.follows:
            entry = Entry.get(Entry.id == self.follows_id)
            while True:
                entries.append(entry)
                if entry.follows_id:
                    try:
                        entry = Entry.get(Entry.id == entry.follows_id)
                    except DoesNotExist:
                        break
                else:
                    break
        if entries:
            return entries[-1]
        return self

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

    @property
    def revision_n(self):
        return (EntryRevision.select()
                .where(EntryRevision.entry == self)
                .count())

    def get_revision(self, version):
        revision = (EntryRevision.select()
                    .where(EntryRevision.entry == self)
                    .order_by(EntryRevision.id)
                    .offset(version or None)
                    .limit(1))
        if revision.count() == 0:
            raise(EntryRevision.DoesNotExist)
        return EntryRevisionWrapper(list(revision)[0])

    # def get_old_version(self, revision_id):
    #     revisions = (EntryRevision.select()
    #                  .where(EntryRevision.entry == self
    #                         and EntryRevision.id >= revision_id)
    #                  .order_by(EntryRevision.id.desc()))
    #     content = self.content
    #     print(content)
    #     print("---")
    #     for revision in revisions:
    #         print(revision.content)
    #         if revision.content:
    #             content = apply_patch(content, revision.content)
    #     return content

    @property
    def stripped_content(self):
        return strip_tags(self.content)

    def get_attachments(self, embedded=False):
        return self.attachments.filter((Attachment.embedded == embedded) &
                                       ~Attachment.archived)

    @property
    def converted_attributes(self):
        "Ensure that the attributes conform to the logbook configuration"
        converted = {}
        for name, value in self.attributes.items():
            try:
                converted[name] = self.logbook.convert_attribute(name, value)
            except ValueError:
                pass
        return converted

    def get_lock(self, ip=None, acquire=False, steal=False):
        """check if there's a lock on the entry, and if an ip is given
        try to acquire it."""
        try:
            lock = EntryLock.get((EntryLock.entry_id == self.id) &
                                 (EntryLock.expires_at > datetime.utcnow()) &
                                 (EntryLock.cancelled_at == None))
            if steal:
                lock.cancel(ip)
                return EntryLock.create(entry=self, owned_by_ip=ip)
            if acquire and ip != lock.owned_by_ip:
                raise self.Locked(lock)
            return lock
        except EntryLock.DoesNotExist:
            if acquire:
                return EntryLock.create(entry=self, owned_by_ip=ip)

    @property
    def lock(self):
        return self.get_lock()

    @classmethod
    def search(cls, logbook=None, followups=False,
               child_logbooks=False, archived=False,
               n=None, offset=0, count=False,
               attribute_filter=None, content_filter=None,
               title_filter=None, author_filter=None,
               attachment_filter=None):

        # Note: this is all pretty messy. The reason we're building
        # the query as a raw string is that peewee does not (currently)
        # support recursive queries, which we need in order to search
        # through nested logbooks. Cleanup needed!
        # TODO: sanitize the SQL queries to prevent bad injections

        if attribute_filter:
            # need to extract the attribute values from JSON here, so that
            # we can match on them later
            attributes = ", {}".format(
                ", ".join(
                    "json_extract(entry.attributes, '$.{attr}') AS {attr_id}"
                    .format(attr=attr, attr_id="attr{}".format(i))
                    for i, (attr, _) in enumerate(attribute_filter)))
        else:
            attributes = ""

        if author_filter:
            # extract the author names as a separate table, so that
            # they can be searched
            # TODO: maybe also take login?
            authors = ", json_each(entry.authors) AS authors2"
        else:
            authors = ""

        if logbook:
            if child_logbooks:
                # recursive query to find all entries in the given logbook
                # or any of its descendants, to arbitrary depth
                query = """
WITH recursive logbook1(id,parent_id) AS (
    values({logbook}, NULL)
    UNION ALL
    SELECT logbook.id, logbook.parent_id FROM logbook,logbook1
    WHERE logbook.parent_id=logbook1.id
)
SELECT {what}{attributes},
       coalesce(followup.follows_id, entry.id) thread,
       count(followup.id) n_followups,
       max(datetime(coalesce(coalesce(followup.last_changed_at,followup.created_at),
                             coalesce(entry.last_changed_at,entry.created_at)))) timestamp
FROM entry{authors}
JOIN logbook1
LEFT JOIN entry AS followup ON entry.id == followup.follows_id
WHERE entry.logbook_id=logbook1.id
""".format(attributes=attributes,
           what="COUNT(distinct(coalesce(followup.follows_id, entry.id))) AS count" if count else "entry.*",
           authors=authors, logbook=logbook.id)
            else:
                # In this case we're not searching recursively
                query = (
                    "select {what}{attributes},coalesce(entry.last_changed_at, entry.created_at) timestamp from entry{authors} where entry.logbook_id = {logbook}"
                    .format(what="count()" if count else "entry.*",
                            logbook=logbook,
                            attributes=attributes,
                            authors=authors))
        else:
            # In this case we're searching all entries and don't need
            # the recursive logbook filtering
            query = """
SELECT {what}{attributes},count(followup.id) n_followups,
       max(datetime(coalesce(coalesce(followup.last_changed_at,followup.created_at),
                    coalesce(entry.last_changed_at,entry.created_at)))) timestamp
FROM entry{authors}
LEFT JOIN entry AS followup ON entry.id == followup.follows_id
WHERE 1
""".format(what="count()" if count else "entry.*",
           attributes=attributes, authors=authors)

        if not archived:
            query += " AND NOT entry.archived"

        # if not followups:
        #     query += " AND entry.follows_id IS NULL"

        # further filters on the results, depending on search criteria
        if content_filter:
            # need to filter out null or REGEX will explode on them
            query += " AND entry.content IS NOT NULL AND entry.content REGEXP '{}'".format(content_filter)
        if title_filter:
            query += " AND entry.title IS NOT NULL AND entry.title REGEXP '{}'".format(title_filter)
        if author_filter:
            query += " AND json_extract(authors2.value, '$.name') REGEXP '{}'".format(author_filter)

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
                query += " AND {} = '{}'".format("attr{}".format(i), value)

        # Here we're getting into deep water...
        # If we just want the total count of results, we can't group
        # because then the count would be per group. So that makes sense.
        # However, when we're searching, we also don't want the grouping
        # because it means we
        if not count:  #,
            query += " GROUP BY entry.id"
            if not any([title_filter, content_filter, author_filter]):
                query += " HAVING entry.follows_id IS NULL"
        # sort newest first, taking into account the last edit if any
        # TODO: does this make sense? Should we only consider creation date?
        query += " ORDER BY timestamp DESC"
        if n:
            query += " LIMIT {}".format(n)
            if offset:
                query += " OFFSET {}".format(offset)
        print(query)
        return Entry.raw(query)


DeferredEntry.set_model(Entry)


class EntryRevision(db.Model):
    """
    Represents a change of an entry.

    Counter-intuitively, what's stored here is the *old* entry
    data. The point is that then we only need to store the fields that
    actually were changed! But it becomes a bit confusing when it's
    time to reconstruct an old entry.
    """

    entry = ForeignKeyField(Entry, related_name="revisions")
    logbook = ForeignKeyField(Logbook, null=True)
    title = CharField(null=True)
    authors = JSONField(null=True)
    content = TextField(null=True)
    metadata = JSONField(null=True)
    attributes = JSONField(null=True)
    follows_id = IntegerField(null=True)
    tags = JSONField(null=True)
    archived = BooleanField(default=False)

    timestamp = DateTimeField(default=datetime.utcnow)
    revision_authors = JSONField(null=True)
    revision_comment = TextField(null=True)
    revision_ip = CharField(null=True)

    def get_attribute(self, attr):
        """Get the value that we were changing to, or the
        current value if it was not changed."""
        try:
            revision = (EntryRevision.select()
                        .where((EntryRevision.entry == self.entry) &
                               (getattr(EntryRevision, attr) != None) &
                               (EntryRevision.id > self.id))
                        .order_by(EntryRevision.id)
                        .get())
            return getattr(revision, attr)
        except DoesNotExist:
            return getattr(self.entry, attr)

    @property
    def content_htmldiff(self):
        if self.content:
            new_content = self.get_attribute("content")
            return htmldiff(self.content, new_content)
        return self.get_attribute("content")

    # @property
    # def current_authors(self):
    #     if self.authors:
    #         return self.authors
    #     return self.get_attribute("authors")

    # @property
    # def current_title(self):
    #     if self.title:
    #         return self.title
    #     return self.get_attribute("title")

    # @property
    # def current_content(self):
    #     if self.content:
    #         return self.content
    #     return self.get_attribute("content")

    # @property
    # def new_title(self):
    #     return self.get_attribute("title")

    # @property
    # def new_authors(self):
    #     return self.get_attribute("authors")

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

    @property
    def revision_n(self):
        revisions = list(self.entry.revisions)
        return revisions.index(self)


class EntryRevisionWrapper:

    """An object that represents a historical version of an entry. It
    can (basically) be used like an Entry object."""

    def __init__(self, revision):
        self.revision = revision

    def __getattr__(self, attr):
        if attr == "id":
            return self.revision.entry.id
        if attr == "last_changed_at":
            return self.revision.timestamp
        # OK, for any of the other entry attributes we want the
        # new value, not the value in the revision which is the old value.
        if attr in ("logbook", "title", "authors", "content", "attributes",
                    "metadata", "follows_id", "tags", "archived"):
            value = self.revision.get_attribute(attr)
            if value is not None:
                return getattr(self.revision, attr)
        try:
            return getattr(self.revision, attr)
        except AttributeError:
            return getattr(self.revision.entry, attr)


class EntryLock(db.Model):
    """Contains temporary edit locks, to prevent overwriting changes.
    An entry can not have more than one lock active at any given time.

    The logic of entry locks works like this:

    - user A wants to edit entry 1.
    - before starting, A acquires a lock on entry 1; lock1A.
    - soon, user B wants to edit entry 1.
    - B tries to acquire a lock on 1, but can't since A already has it.
    - B is prevented from unknowingly conflicting with A!
    - B can now either:
       + wait for A to submit his/her edits and then try again,
       + wait for the lock to expire (which it will, in, say 1h)
       + "steal" the lock.
    - If B steals the lock it means that A no longer has the lock, and
      might be in for a nasty surprise when he/she tries to submit later.
    - When submitting an edit, it's necessary to include the
      "last_changed_at" field of the version that was edited. This
      way, the server can check if the entry has been changed meanwhile.
      If this is not the case, and nobody else has locked the entry, it's
      allowed. Note that it does not matter if the lock has expired. It's
      not necessary to acquire a lock to do an edit, it's just polite.
    - B might know that A is no longer interested in the edit, so it makes
      sense to make the option of stealing available, as long as it's
      explicit.
    - When the owner of a lock submits changes to the locked entry, the
      lock is automatically cancelled.
    - The owher of a lock can also choose to cancel it without writing the
      entry. Otherwise it will also expire after a while.

    The point of locking is to make it harder for users to overwrite
    each others changes *by mistake*, not to make it impossible.

    """
    entry = ForeignKeyField(Entry)
    created_at = DateTimeField(default=datetime.utcnow)
    expires_at = DateTimeField(default=(lambda: datetime.utcnow() +
                                        timedelta(hours=1)))
    owned_by_ip = CharField()
    cancelled_at = DateTimeField(null=True)
    cancelled_by_ip = CharField(null=True)

    @property
    def locked(self):
        return not self.cancelled_at and self.expires_at > datetime.utcnow()

    def cancel(self, ip):
        self.cancelled_at = datetime.utcnow()
        self.cancelled_by_ip = ip
        self.save()


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
