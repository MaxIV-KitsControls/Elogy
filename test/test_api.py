from io import BytesIO
import json

from pytest import mark

from .fixtures import elogy_client


def post_json(client, url, data, **kwargs):
    return client.post(url, data=json.dumps(data),
                       content_type='application/json', **kwargs)


def decode_response(response):
    return json.loads(response.get_data().decode("utf-8"))


def make_logbook(client, data=None):
    in_logbook = data or dict(
        name="Test logbook",
        description="Test description")
    response = client.post("/api/logbooks/", data=in_logbook)
    assert response.status_code == 200
    return in_logbook, decode_response(response)["logbook"]


def make_entry(client, logbook, data=None):
    in_entry = data or dict(
        title="Test entry",
        content="This is some test content!",
        content_type="text/plain")
    response = post_json(
        client,
        "/api/logbooks/{logbook[id]}/entries/".format(logbook=logbook),
        data=in_entry)
    assert response.status_code == 200
    return in_entry, decode_response(response)["entry"]


def test_create_logbook(elogy_client):

    in_logbook, logbook = make_logbook(elogy_client)

    # read it back
    out_logbook = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/"
                         .format(logbook=logbook)))["logbook"]

    assert in_logbook["name"] == out_logbook["name"]
    assert in_logbook["description"] == out_logbook["description"]


def test_create_child_logbook(elogy_client):

    in_logbook, logbook = make_logbook(elogy_client)

    # make a child logbook
    child = decode_response(
        post_json(
            elogy_client,
            "/api/logbooks/{logbook[id]}/".format(logbook=logbook),
            data={"name": "Some name"}))["logbook"]
    assert child["parent"]["id"] == logbook["id"]

    # check that it also comes up as child
    parent = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/"
                         .format(logbook=logbook)))["logbook"]
    assert parent["children"][0]["id"] == child["id"]


def test_update_logbook(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)

    # read it back
    out_logbook = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/"
                         .format(logbook=logbook)))["logbook"]

    response = decode_response(
        elogy_client.put(
            "/api/logbooks/{}/".format(out_logbook["id"]),
            data=dict(name="New name",
                      description=out_logbook["description"])))["logbook"]
    assert response["name"] == "New name"


def test_move_logbook(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)
    in_logbook2, logbook2 = make_logbook(elogy_client)

    response = decode_response(
        elogy_client.put(
            "/api/logbooks/{}/".format(logbook["id"]),
            data=dict(parent_id=logbook2["id"])))["logbook"]

    # read it back
    out_logbook = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/"
                         .format(logbook=logbook)))["logbook"]

    assert response["parent"]["id"] == logbook2["id"]

    # check that the logbook is now the child of the parent
    parent_logbook = decode_response(
        elogy_client.get("/api/logbooks/{logbook[parent][id]}/"
                         .format(logbook=response)))["logbook"]

    assert parent_logbook["children"][0]["id"] == logbook["id"]


def test_create_entry(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    # read the entry back
    out_entry = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook, entry=entry)))["entry"]

    assert out_entry["title"] == in_entry["title"]
    assert out_entry["content"] == in_entry["content"]
    assert out_entry["id"] == entry["id"]


def test_update_entry(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    # change the title
    new_in_entry = {**in_entry,
                    "title": "New title",
                    "revision_n": 0}
    out_entry = decode_response(
        elogy_client.put("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook, entry=entry),
                         data=new_in_entry))["entry"]
    print(out_entry)
    assert out_entry["title"] == new_in_entry["title"]
    assert out_entry["content"] == new_in_entry["content"]
    assert out_entry["id"] == entry["id"]

    # verify that the new revision can be retrieved
    new_entry_version = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook, entry=entry)))["entry"]
    assert new_entry_version == out_entry
    assert new_entry_version["revision_n"] == 1

    # verify that the original revision is available
    old_entry_version = decode_response(
        elogy_client.get(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/revisions/0"
            .format(logbook=logbook, entry=entry)))["entry"]
    assert old_entry_version["title"] == in_entry["title"]
    assert old_entry_version["revision_n"] == 0

    revisions = decode_response(
        elogy_client.get(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/revisions/"
            .format(logbook=logbook, entry=entry)))["entry_changes"]


def test_move_entry(elogy_client):
    in_logbook1, logbook1 = make_logbook(elogy_client)
    in_logbook2, logbook2 = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook1)

    # change the logbook
    new_in_entry = {**in_entry,
                    "logbook_id": logbook2["id"],
                    "revision_n": 0}
    out_entry = decode_response(
        elogy_client.put("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook1, entry=entry),
                         data=new_in_entry))["entry"]
    assert out_entry["logbook"]["id"] == logbook2["id"]

    # verify that the new revision can be retrieved
    new_entry_version = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook2, entry=entry)))["entry"]
    assert new_entry_version == out_entry
    assert new_entry_version["revision_n"] == 1

    # verify that the original revision is available
    old_entry_version = decode_response(
        elogy_client.get(
            "/api/entries/{entry[id]}/revisions/0"
            .format(entry=entry)))["entry"]
    print(old_entry_version)
    assert old_entry_version["logbook"]["id"] == logbook1["id"]
    assert old_entry_version["revision_n"] == 0

    revisions = decode_response(
        elogy_client.get(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/revisions/"
            .format(logbook=logbook2, entry=entry)))["entry_changes"]


def test_create_entry_followup(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    # make a followup to the entry. This is like a "reply", but the idea is
    # that only immediate replies to a toplevel entry count as followups.
    # It's possible to reply to a reply, but these will not show up e.g.
    # in the list of entries (unless they specifically match a search).
    in_followup = dict(
        title="Test followup",
        content="This is some followup test content!",
        content_type="text/plain")
    followup = decode_response(
        post_json(elogy_client,
                  "/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                  .format(logbook=logbook, entry=entry),
                  data=in_followup))["entry"]

    # get the followup directly
    out_followup = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{followup[id]}/"
                         .format(logbook=logbook, followup=followup)))["entry"]
    assert out_followup["id"] == followup["id"]

    # read the parent entry back
    out_entry = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook, entry=entry)))["entry"]

    assert out_entry["followups"][0]["id"] == followup["id"]

    # check that we get the parent when asking for the whole "thread"
    out_thread = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{followup[id]}/"
                         .format(logbook=logbook, followup=followup),
                         data={"thread": True}))["entry"]
    assert out_thread["id"] == entry["id"]


def test_update_entry_conflict(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    # change the title
    new_in_entry = {**in_entry, "title": "New title",
                    "revision_n": entry["revision_n"]}
    out_entry = decode_response(
        elogy_client.put("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook, entry=entry),
                         data=new_in_entry))["entry"]

    # try to change the entry again, without last_changed_at
    new_in_entry2 = {**in_entry, "title": "Other title"}
    result = elogy_client.put(
        "/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
        .format(logbook=logbook, entry=entry),
        data=new_in_entry2)
    assert result.status_code == 400

    # try to change the entry again, with incorrect last_changed_at
    new_in_entry2 = {**in_entry, "title": "Other title", "revision_n": 0}
    result = elogy_client.put(
        "/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
        .format(logbook=logbook, entry=entry),
        data=new_in_entry2)
    assert result.status_code == 409

    # try to change the entry again, with correct last_changed_at
    new_in_entry2 = {**in_entry, "title": "Other title",
                     "revision_n": 1}
    result = elogy_client.put(
        "/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
        .format(logbook=logbook, entry=entry),
        data=new_in_entry2)
    assert result.status_code == 200


def test_entry_lock(elogy_client):

    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    IP = '1.2.3.4'

    lock = decode_response(
        elogy_client.post(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry),
            environ_base={'REMOTE_ADDR': IP}))["lock"]

    assert lock["owned_by_ip"] == IP

    # verify that the entry is locked
    get_lock = decode_response(
        elogy_client.get(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry)))["lock"]
    assert get_lock["id"] == lock["id"]

    # acquire the lock again from the same host
    lock_again = decode_response(
        elogy_client.post(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry),
            environ_base={'REMOTE_ADDR': IP}))["lock"]

    # should be the same lock
    assert lock_again["id"] == lock["id"]

    # try to change the entry from the same host
    edit_entry = elogy_client.put(
        "/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
        .format(logbook=logbook, entry=entry),
        data=dict(title="New title",
                  revision_n=entry["revision_n"]),
        environ_base={'REMOTE_ADDR': IP})
    assert edit_entry.status_code == 200

    # verify that the entry is no longer locked
    no_lock = elogy_client.get(
        "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
        .format(logbook=logbook, entry=entry))
    assert no_lock.status_code == 404


def test_entry_lock_conflict(elogy_client):

    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    IP = '1.2.3.4'

    lock = decode_response(
        elogy_client.post(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry),
            environ_base={'REMOTE_ADDR': IP}))["lock"]

    # attempt to acquire a lock from another host
    OTHER_IP = '5.6.7.8'
    other_lock = elogy_client.post(
        "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
        .format(logbook=logbook, entry=entry),
        environ_base={'REMOTE_ADDR': OTHER_IP})

    # it should fail with a conflict
    assert other_lock.status_code == 409

    # try to change the entry from another host
    other_edit_entry = elogy_client.put(
        "/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
        .format(logbook=logbook, entry=entry),
        data=dict(title="New title", revision_n=0),
        environ_base={'REMOTE_ADDR': OTHER_IP})

    assert other_edit_entry.status_code == 409

    # now cancel the lock
    cancelled_lock = decode_response(
        elogy_client.delete(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry),
            data={"lock_id": lock["id"]}))["lock"]
    assert cancelled_lock["cancelled_at"] is not None

    # acquire the lock from the other host
    other_lock2 = decode_response(
        elogy_client.post(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry),
            environ_base={'REMOTE_ADDR': OTHER_IP}))["lock"]
    assert other_lock2["owned_by_ip"] == OTHER_IP


def test_entry_lock_steal(elogy_client):

    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    IP = '1.2.3.4'

    # acquire a lock on the entry
    lock = decode_response(
        elogy_client.post(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry),
            environ_base={'REMOTE_ADDR': IP}))["lock"]

    # attempt to acquire a lock from another host
    OTHER_IP = '5.6.7.8'
    other_lock = elogy_client.post(
        "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
        .format(logbook=logbook, entry=entry),
        environ_base={'REMOTE_ADDR': OTHER_IP})

    # it should fail with a conflict
    assert other_lock.status_code == 409

    # explicitly steal the lock
    stolen_lock = decode_response(
        post_json(elogy_client,
                  "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
                  .format(logbook=logbook, entry=entry),
                  data=dict(steal=True),
                  environ_base={'REMOTE_ADDR': OTHER_IP}))["lock"]
    assert stolen_lock["id"] != lock["id"]

    # verify that the entry lock has changed
    lock2 = decode_response(
        elogy_client.get(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry)))["lock"]
    assert lock2["id"] == stolen_lock["id"]
    assert lock2["owned_by_ip"] == OTHER_IP


def test_create_attachment(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    # upload an attachment
    FILENAME = "my_attachment.txt"
    DATA = b"some data"
    URL = ("/api/logbooks/{logbook[id]}/entries/{entry[id]}/attachments/"
           .format(logbook=logbook, entry=entry))

    att = decode_response(
        elogy_client.post(
            URL,
            content_type='multipart/form-data',
            data={"attachment": [(BytesIO(DATA), FILENAME)]}))
    assert att["filename"] == FILENAME

    # read it back
    attachment = elogy_client.get(att["location"])
    assert attachment.get_data() == DATA

    # check that the entry now also has the attachment
    response = decode_response(elogy_client.get(
        "/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
        .format(logbook=logbook, entry=entry)))
    assert response["entry"]["attachments"][0]["id"] == att["id"]


@mark.xfail(reason="See https://github.com/pallets/werkzeug/issues/1091")
def test_create_attachment_with_single_quotes(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    # upload an attachment
    FILENAME = "my_'attachment'.txt"
    DATA = b"some data"
    URL = ("/api/logbooks/{logbook[id]}/entries/{entry[id]}/attachments/"
           .format(logbook=logbook, entry=entry))

    att = decode_response(
        elogy_client.post(
            URL,
            content_type='multipart/form-data',
            data={"attachment": [(BytesIO(DATA), FILENAME)]}))
    assert att["filename"] == FILENAME


def test_entry_search(elogy_client):

    # TODO: expand to cover all ways to search

    # create a bunch of logbooks and entries
    in_logbook1, logbook1 = make_logbook(elogy_client)
    in_entry11, entry11 = make_entry(elogy_client, logbook1,
                                     {"title": "A1",
                                      "content": "Some content"})
    in_entry12, entry12 = make_entry(elogy_client, logbook1,
                                     {"title": "B1",
                                      "content": "Some more content"})
    in_entry13, entry13 = make_entry(elogy_client, logbook1,
                                     {"title": "C1", "follows_id": entry12["id"],
                                      "content": "More different content"})
    in_logbook2, logbook2 = make_logbook(elogy_client)
    in_entry21, entry21 = make_entry(elogy_client, logbook2,
                                     {"title": "A2",
                                      "content": "Some content"})
    in_entry22, entry22 = make_entry(elogy_client, logbook2,
                                     {"title": "B2",
                                      "content": "Some more content",
                                      "follows_id": entry21["id"]})
    in_entry23, entry23 = make_entry(elogy_client, logbook2,
                                     {"title": "C2", "follows_id": entry22["id"],
                                      "content": "Further different content"})

    # search logbook
    URL = ("/api/logbooks/{logbook[id]}/entries/?content=more".format(logbook=logbook1))
    result = decode_response(elogy_client.get(URL))
    assert set([entry12["id"], entry13["id"]]) == set(e["id"] for e in result["entries"])

    # search all logbooks
    URL = ("/api/logbooks/0/entries/?content=more")
    result = decode_response(elogy_client.get(URL))
    assert set([entry12["id"], entry13["id"], entry22["id"]]) == set(e["id"] for e in result["entries"])
