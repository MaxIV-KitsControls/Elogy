"""
Some tests that exercise the server.
"""

from random import random, randint, choice
from string import ascii_letters

from faker import Faker

from .fixtures import elogy_client as client
from .providers import ElogyProvider
from .test_api import make_logbook, post_json, decode_response


fake = Faker()
fake.add_provider(ElogyProvider)


def test_create_entries(client):

    _, lb = make_logbook(client)

    # create a bunch of entries
    entries = [fake.entry() for i in range(1000)]
    ids = []
    for entry in entries:
        response = decode_response(
            post_json(
                client,
                "/api/logbooks/{logbook[id]}/entries/".format(logbook=lb),
                data=entry))
        ids.append(response["entry"]["id"])

    # read back and verify that the data is correct
    for entry, entry_id in zip(entries, ids):
        remote = decode_response(client.get(
            "/api/logbooks/{logbook[id]}/entries/{entry_id}/"
            .format(logbook=lb, entry_id=entry_id)))
        assert remote["entry"]["id"] == entry_id
        assert remote["entry"]["title"] == entry["title"]
        assert remote["entry"]["authors"] == entry["authors"]
        # assert remote["entry"]["content"] == entry["content"]  # stripped!
        assert remote["entry"]["content_type"] == entry["content_type"]


def test_search_content(client):

    _, lb = make_logbook(client)

    # create a bunch of entries, some of which contain a random string (term)
    entries = [fake.text_entry() for i in range(1000)]
    hits = set()
    term = "".join(choice(ascii_letters) for i in range(randint(5, 10)))
    for entry in entries:
        hit = random() < 0.1
        if hit:
            content = entry["content"]
            position = randint(0, len(content)-1)
            entry["content"] = content[:position] + term + content[position:]
        response = decode_response(
            post_json(
                client,
                "/api/logbooks/{logbook[id]}/entries/".format(logbook=lb),
                data=entry))
        if hit:
            hits.add(response["entry"]["id"])

    # do a search for the term
    search = decode_response(client.get("/api/logbooks/{logbook[id]}/entries/?content={term}&n=1000"
                                        .format(logbook=lb, term=term)))

    # check that we found the correct entries
    assert len(search["entries"]) == len(hits)
    for entry in search["entries"]:
        assert entry["id"] in hits
        hits.remove(entry["id"])
    assert not hits
