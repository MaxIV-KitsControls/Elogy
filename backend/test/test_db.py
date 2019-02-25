from datetime import datetime
from operator import attrgetter

from .fixtures import db
from backend.db import Entry
from backend.db import Logbook, LogbookRevision


# Logbook

def test_logbook(db):
    lb = Logbook.create(name="Logbook1", description="Hello")
    assert lb.name == "Logbook1"
    assert lb.description == "Hello"


def test_logbook_descendants(db):
    parent1 = Logbook.create(name="Logbook1")
    parent2 = Logbook.create(name="Logbook2")
    child1 = Logbook.create(name="Logbook3", parent=parent1)
    child2 = Logbook.create(name="Logbook4", parent=parent1)
    child1child1 = Logbook.create(name="Logbook5", parent=child1)
    desc_ids = parent1.descendants
    assert set(desc_ids) == set([child1, child2, child1child1])


def test_logbook_ancestors(db):
    parent1 = Logbook.create(name="Logbook1")
    parent2 = Logbook.create(name="Logbook2")
    child1 = Logbook.create(name="Logbook3", parent=parent1)
    child2 = Logbook.create(name="Logbook4", parent=parent1)
    child1child1 = Logbook.create(name="Logbook5", parent=child1)
    desc_ids = child1child1.ancestors
    assert set(desc_ids) == set([parent1, child1])


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


def test_entry_date_search(db):
    lb = Logbook.create(name="Logbook1")

    entries = [
        {
            "logbook": lb,
            "title": "Z",
            "content": "This content is great!",
            "created_at": datetime(2019, 1, 14, 12, 0, 0)
        },
        {
            "logbook": lb,
            "title": "A",
            "content": "This content is great!",
            "created_at": datetime(2019, 1, 15, 12, 0, 0)
        },
        {
            "logbook": lb,
            "title": "B",
            "content": "Some very neat content.",
            "created_at": datetime(2019, 1, 17, 12, 0, 0)
        },
        {
            "logbook": lb,
            "title": "C",
            "content": "Not so bad content either.",
            "created_at": datetime(2019, 1, 18, 12, 0, 0)
        },
        {
            "logbook": lb,
            "title": "C",
            "content": "Not so bad content either.",
            "created_at": datetime(2019, 1, 19, 12, 0, 0),
            "last_changed_at": datetime(2019, 2, 6, 12, 0, 0)
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    # include the from date
    results = list(Entry.search(logbook=lb, from_timestamp=datetime(2019, 1, 17, 0, 0, 0)))
    assert {r.title for r in results} == {"B", "C"}

    # include the until_date
    results = list(Entry.search(logbook=lb, until_timestamp=datetime(2019, 1, 17, 23, 59, 59)))
    assert {r.title for r in results} == {"Z", "A", "B"}

    # date interval
    results = list(Entry.search(logbook=lb,
                                from_timestamp=datetime(2019, 1, 15, 0, 0, 0),
                                until_timestamp=datetime(2019, 1, 17, 23, 59, 59)))
    assert {r.title for r in results} == {"A", "B"}

    # also looks at change timestamp
    results = list(Entry.search(logbook=lb, from_timestamp=datetime(2019, 2, 1)))
    assert {r.title for r in results} == {"C"}


def test_entry_search_followups(db):
    lb = Logbook.create(name="Logbook1")

    entries = [
        {
            "logbook": lb,
            "title": "First entry",
            "content": "This content is great!"
        },
        {
            "logbook": lb,
            "follows_id": 1,
            "title": "Second entry",
            "content": "Some very neat content."
        },
        {
            "logbook": lb,
            "follows_id": 2,
            "title": "Third entry",
            "content": "Not so bad content either."
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    # simple search
    result, = list(Entry.search(logbook=lb))
    assert result.title == "First entry"


def test_entry_attribute_search_followups(db):
    lb = Logbook.create(name="Logbook1")

    entries = [
        {
            "logbook": lb,
            "title": "First entry",
            "content": "This content is great!"
        },
        {
            "logbook": lb,
            "follows_id": 1,
            "title": "Second entry",
            "content": "Some very neat content.",
            "attributes": {"a": 1}
        },
        {
            "logbook": lb,
            "follows_id": 2,
            "title": "Third entry",
            "content": "Not so bad content either."
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    # simple search
    result, = list(Entry.search(logbook=lb, followups=True, attribute_filter=[("a", 1)]))
    assert result.title == "Second entry"


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
    print(set(map(attrgetter("title"), results)))
    assert set(map(attrgetter("title"), results)) == set(["First entry",
                                                          "Second entry"])

    # either
    results = list(Entry.search(logbook=lb, author_filter="alpha|beta"))
    assert set(map(attrgetter("title"), results)) == set(["First entry",
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
    assert set([results[0].title, results[1].title]) == set(["First entry",
                                                             "Third entry"])

    # multiple attribute filter
    results = list(Entry.search(logbook=lb,
                                attribute_filter=[("a", 2), ("b", "2")]))
    assert len(results) == 1
    assert results[0].title == "Third entry"


def test_entry_attribute_multioption_filter(db):

    """
    All the values given for each attribute must be
    present in the options selected.
    """

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
            "attributes": {"a": ["2"], "b": ["7"]}
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

    # one value matching several entries
    results = list(Entry.search(logbook=lb, attribute_filter=[("a", "2")]))
    assert len(results) == 2
    set([results[0].title, results[0].title]) == set(["First entry",
                                                      "Second entry"])

    # two values for one attribute
    results = list(Entry.search(logbook=lb, attribute_filter=[("a", "2"),
                                                              ("a", "3")]))
    assert len(results) == 1
    set([results[0].title, results[0].title]) == set(["First entry"])

    # two different attributes
    results = list(Entry.search(logbook=lb, attribute_filter=[("a", "2"),
                                                              ("b", "7")]))
    assert len(results) == 1
    set([results[0].title, results[0].title]) == set(["Second entry"])


def test_entry_metadata_filter(db):

    lb = Logbook.create(name="Logbook1")

    entries = [
        {
            "logbook": lb,
            "title": "First entry",
            "content": "This content is great!",
            "metadata": {"message": "hello"}
        },
        {
            "logbook": lb,
            "title": "Second entry",
            "content": "Some very neat content.",
            "metadata": {"message": "yellow"}
        },
        {
            "logbook": lb,
            "title": "Third entry",
            "content": "Not so bad content either.",
            "metadata": {}
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    # filter attributes
    result, = list(Entry.search(logbook=lb, metadata_filter=[("message", "hello")]))
    assert result.title == "First entry"

    results = list(Entry.search(logbook=lb, metadata_filter=[("message", "%ello%")]))
    assert len(results) == 2
    set([results[0].title, results[0].title]) == set(["First entry",
                                                      "Second entry"])


def test_entry_content_search_child_logbooks(db):

    """Searching a logbook with 'child_logbooks' should also return
    hits from all descendant logbooks"""

    parent_lb = Logbook.create(name="Logbook1")
    child_lb = Logbook.create(name="Logbook2", parent=parent_lb)
    grandchild_lb = Logbook.create(name="Logbook2", parent=child_lb)

    entries = [
        {
            "logbook": parent_lb,
            "title": "entry1",
            "content": "This content is great!",
        },
        {
            "logbook": child_lb,
            "title": "entry2",
            "content": "Some very neat content.",
        },
        {
            "logbook": grandchild_lb,
            "title": "entry3",
            "content": "Other stuff.",
        },
        {
            "logbook": grandchild_lb,
            "title": "entry4",
            "content": "Not so bad content either.",
        },
        {
            "logbook": grandchild_lb,
            "title": "entry5",
            "content": "Other stuff.",
        }
    ]

    # create entries
    for entry in entries:
        entry = Entry.create(**entry)
        entry.save()

    # only parent logbook
    results = list(Entry.search(logbook=parent_lb, child_logbooks=False,
                                content_filter="content"))
    assert len(results) == 1
    assert results[0].title == "entry1"

    # include child logbooks
    results = list(Entry.search(logbook=parent_lb, child_logbooks=True,
                                content_filter="content"))
    assert len(results) == 3
    assert set(r.title for r in results) == {"entry1", "entry2", "entry4"}

    # more restrictive
    results = list(Entry.search(logbook=parent_lb, child_logbooks=True,
                                content_filter="neat content"))

    assert len(results) == 1
    set([results[0].title]) == "entry2"
