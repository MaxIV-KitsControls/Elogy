from operator import attrgetter

from .fixtures import db
from elogy.db import Entry, EntryChange, EntryRevision
from elogy.db import Logbook, LogbookChange, LogbookRevision


# Logbook

def test_logbook(db):
    lb = Logbook.create(name="Logbook1", description="Hello")
    assert lb.name == "Logbook1"
    assert lb.description == "Hello"


def test_logbook_entries(db):
    lb = Logbook.create(name="Logbook1", description="Hello")
    entry2 = Entry.create(logbook=lb, title="Entry1")
    entry2 = Entry.create(logbook=lb, title="Entry1")
    assert len(lb.entries) == 2


def test_logbookrevision(db):
    lb = Logbook.create(name="Logbook1", description="Hello")
    # to properly update the logbook, use the "make_change" method
    # which creates a revision.
    revision = lb.make_change(name="Logbook2")
    # remember to save both logbook and revision
    lb.save()
    revision.save()

    assert len(lb.changes) == 1
    rev = lb.changes[0]
    assert rev == revision
    # old value is stored in the revision
    assert rev.changed["name"] == "Logbook1"


def test_logbookrevisionwrapper1(db):
    lb = Logbook.create(name="Logbook1", description="Hello")
    lb.make_change(name="Logbook2").save()
    lb.save()

    #The wrapper should look like a historical version of  a Logbook
    wrapper = lb.get_revision(version=0)
    assert wrapper.name == "Logbook1"


def test_logbookrevisionwrapper2(db):
    DESCRIPTION = "Hello"
    lb = Logbook.create(name="Logbook1", description=DESCRIPTION)
    lb.make_change(name="Logbook2").save()
    lb.save()
    lb.make_change(name="Logbook3").save()
    lb.save()

    wrapper = lb.get_revision(version=0)
    assert isinstance(wrapper, LogbookRevision)
    assert wrapper.revision_n == 0
    assert wrapper.name == "Logbook1"
    assert wrapper.description == DESCRIPTION

    wrapper = lb.get_revision(version=1)
    assert isinstance(wrapper, LogbookRevision)
    assert wrapper.revision_n == 1
    assert wrapper.name == "Logbook2"
    assert wrapper.description == DESCRIPTION

    wrapper = lb.get_revision(version=2)
    assert wrapper == lb  # newest revision is just the Logbook
    assert wrapper.revision_n == 2
    assert wrapper.name == "Logbook3"
    assert wrapper.description == DESCRIPTION


def test_logbookrevisionwrapper3(db):
    NAME1 = "Name1"
    NAME2 = "Name2"
    DESCRIPTION1 = "Original description"
    DESCRIPTION2 = "New description"
    lb = Logbook.create(name=NAME1, description=DESCRIPTION1)
    lb.make_change(name=NAME2, description=DESCRIPTION2).save()
    lb.save()
    lb.make_change(name=NAME1).save()
    lb.save()

    wrapper = lb.get_revision(version=0)
    assert wrapper.name == NAME1
    assert wrapper.description == DESCRIPTION1

    wrapper = lb.get_revision(version=1)
    assert wrapper.name == NAME2
    assert wrapper.description == DESCRIPTION2

    wrapper = lb.get_revision(version=2)
    assert wrapper.name == NAME1
    assert wrapper.description == DESCRIPTION2
    assert wrapper == lb  # newest revision is just the Logbook


# Entry

def test_entry(db):
    lb = Logbook.create(name="Logbook1", description="Hello")
    entry = Entry(logbook=lb, title="Entry1", content="Some content here")
    assert entry.logbook == lb
    assert entry.title == "Entry1"


def test_enryrevision(db):
    lb = Logbook.create(name="Logbook1", description="Hello")
    entry = Entry.create(logbook=lb, title="Entry1")
    revision = entry.make_change(title="Entry2")
    entry.save()
    revision.save()

    assert len(entry.changes) == 1
    rev = entry.changes[0]
    assert rev == revision
    assert rev.changed["title"] == "Entry1"


def test_entryrevisionwrapper1(db):
    lb = Logbook.create(name="Logbook1")
    entry = Entry.create(logbook=lb, title="Entry1")
    entry.make_change(title="Entry2").save()
    entry.save()
    wrapper = entry.get_revision(version=0)
    assert wrapper.revision_n == 0
    assert wrapper.title == "Entry1"


def test_entryrevisionwrapper2(db):
    lb = Logbook.create(name="Logbook1")

    entry_v0 = {
        "logbook": lb,
        "title": "Some nice title",
        "content": "Some very neat content."
    }

    entry_v1 = {
        "logbook": lb,
        "title": "Some really nice title",
        "content": "Some very neat content."
    }

    entry_v2 = {
        "logbook": lb,
        "title": "Some really nice title",
        "content": "Some very neat content but changed."
    }

    # create entry and modify it twice
    entry = Entry.create(**entry_v0)
    entry.make_change(**entry_v1).save()
    entry.save()
    entry.make_change(**entry_v2).save()
    entry.save()

    # check that the wrapper reports the correct historical
    # values for each revision
    wrapper0 = entry.get_revision(version=0)
    assert wrapper0.revision_n == 0
    assert wrapper0.title == entry_v0["title"]
    assert wrapper0.content == entry_v0["content"]

    wrapper1 = entry.get_revision(version=1)
    assert wrapper1.revision_n == 1
    assert wrapper1.title == entry_v1["title"]
    assert wrapper1.content == entry_v1["content"]

    wrapper2 = entry.get_revision(version=2)
    assert wrapper2.revision_n == 2
    assert wrapper2.title == entry_v2["title"]
    assert wrapper2.content == entry_v2["content"]


# Search

def test_entry_content_search(db):
    lb1 = Logbook.create(name="Logbook1")
    lb2 = Logbook.create(name="Logbook2")

    entries = [
        {
            "logbook": lb1,
            "title": "First entry",
            "content": "This content is great!"
        },
        {
            "logbook": lb1,
            "title": "Second entry",
            "content": "Some very neat content."
        },
        {
            "logbook": lb1,
            "title": "Third entry",
            "content": "Not so bad content either."
        },
        {
            "logbook": lb2,
            "title": "Fourth entry",
            "content": "Not so great content, should be ignored."
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    # simple search
    result, = list(Entry.search(logbook=lb1, content_filter="great"))
    assert result.title == "First entry"

    # regexp search
    result, = list(Entry.search(logbook=lb1, content_filter="Not.*content"))
    assert result.title == "Third entry"


def test_entry_content_search_global(db):
    lb = Logbook.create(name="Logbook1")

    entries = [
        {
            "logbook": lb,
            "title": "First entry",
            "content": "This content is great!"
        },
        {
            "logbook": lb,
            "title": "Second entry",
            "content": "Some very neat content."
        },
        {
            "logbook": lb,
            "title": "Third entry",
            "content": "Not so bad content either."
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    # simple search
    result, = list(Entry.search(content_filter="great"))
    assert result.title == "First entry"

    # regexp search
    result, = list(Entry.search(content_filter="Not.*content"))
    assert result.title == "Third entry"


def test_entry_title_search(db):
    lb = Logbook.create(name="Logbook1")

    entries = [
        {
            "logbook": lb,
            "title": "First entry",
            "content": "This content is great!"
        },
        {
            "logbook": lb,
            "title": "Second entry",
            "content": "Some very neat content."
        },
        {
            "logbook": lb,
            "title": "Third entry",
            "content": "Not so bad content either."
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    # simple search
    result, = list(Entry.search(logbook=lb, title_filter="First"))
    assert result.title == "First entry"

    # regexp search
    result, = list(Entry.search(logbook=lb, title_filter="Th.*ry"))
    assert result.title == "Third entry"


def test_entry_authors_search(db):
    lb = Logbook.create(name="Logbook1")

    entries = [
        {
            "logbook": lb,
            "title": "First entry",
            "content": "This content is great!",
            "authors": [{"name": "alpha"}, {"name": "beta"}]
        },
        {
            "logbook": lb,
            "title": "Second entry",
            "content": "Some very neat content.",
            "authors": [{"name": "alpha"}]
        },
        {
            "logbook": lb,
            "title": "Third entry",
            "content": "Not so bad content either.",
            "authors": [{"name": "gamma"}, {"name": "beta"}]
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    results = list(Entry.search(logbook=lb, author_filter="alpha"))
    set([results[0].title, results[0].title]) == set(["First entry",
                                                      "Second entry"])

    # either
    results = list(Entry.search(logbook=lb, author_filter="alpha|beta"))
    set(map(attrgetter("title"), results)) == set(["First entry",
                                                   "Second entry",
                                                   "Third entry"])


def test_entry_attribute_filter(db):
    lb = Logbook.create(name="Logbook1")

    entries = [
        {
            "logbook": lb,
            "title": "First entry",
            "content": "This content is great!",
            "attributes": {"a": 1, "b": "2"}
        },
        {
            "logbook": lb,
            "title": "Second entry",
            "content": "Some very neat content.",
            "attributes": {"a": 1, "b": "3"}
        },
        {
            "logbook": lb,
            "title": "Third entry",
            "content": "Not so bad content either.",
            "attributes": {"a": 2, "b": "2"}
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    # filter attributes
    result, = list(Entry.search(logbook=lb, attribute_filter=[("a", 2)]))
    assert result.title == "Third entry"

    results = list(Entry.search(logbook=lb, attribute_filter=[("b", "2")]))
    assert len(results) == 2
    set([results[0].title, results[0].title]) == set(["First entry",
                                                      "Third entry"])


def test_entry_attribute_multioption_filter(db):

    lb = Logbook.create(name="Logbook1")

    entries = [
        {
            "logbook": lb,
            "title": "First entry",
            "content": "This content is great!",
            "attributes": {"a": ["1", "2", "3"]}
        },
        {
            "logbook": lb,
            "title": "Second entry",
            "content": "Some very neat content.",
            "attributes": {"a": ["2"]}
        },
        {
            "logbook": lb,
            "title": "Third entry",
            "content": "Not so bad content either.",
            "attributes": {"a": ["3", "4"]}
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    # filter attributes
    result, = list(Entry.search(logbook=lb, attribute_filter=[("a", "1")]))
    assert result.title == "First entry"

    results = list(Entry.search(logbook=lb, attribute_filter=[("a", "2")]))
    assert len(results) == 2
    set([results[0].title, results[0].title]) == set(["First entry",
                                                      "Second entry"])
