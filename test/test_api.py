import json

from .fixtures import elogy_client


def decode_response(response):
    return json.loads(response.get_data().decode("utf-8"))


def make_logbook(client):
    in_logbook = dict(
        name="Test logbook",
        description="Test description")
    response = client.post("/api/logbooks/", data=in_logbook)
    assert response.status_code == 200
    return in_logbook, decode_response(response)


def make_entry(client, logbook):
    in_entry = dict(
        title="Test entry",
        content="This is some test content!",
        content_type="text/plain")
    response = client.post(
        "/api/logbooks/{logbook[id]}/entries/".format(logbook=logbook),
        data=in_entry)
    assert response.status_code == 200
    return in_entry, decode_response(response)


def test_create_logbook(elogy_client):

    in_logbook, logbook = make_logbook(elogy_client)

    # read it back
    out_logbook = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/"
                         .format(logbook=logbook)))

    assert in_logbook["name"] == out_logbook["name"]
    assert in_logbook["description"] == out_logbook["description"]


def test_create_child_logbook(elogy_client):

    in_logbook, logbook = make_logbook(elogy_client)

    # make a child logbook
    child = decode_response(
        elogy_client.post("/api/logbooks/{logbook[id]}/"
                          .format(logbook=logbook),
                          data={"name": "Some name"}))
    assert child["parent"]["id"] == logbook["id"]

    # check that it also comes up as child
    parent = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/"
                         .format(logbook=logbook)))
    assert parent["children"][0]["id"] == child["id"]


def test_update_logbook(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)

    # read it back
    out_logbook = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/"
                         .format(logbook=logbook)))

    response = decode_response(
        elogy_client.put("/api/logbooks/{}/".format(out_logbook["id"]),
                         data=dict(name="New name",
                                   description=out_logbook["description"])))


def test_create_entry(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    # read the entry back
    out_entry = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook, entry=entry)))

    assert out_entry["title"] == in_entry["title"]
    assert out_entry["content"] == in_entry["content"]
    assert out_entry["id"] == entry["id"]


def test_update_entry(elogy_client):
    in_logbook, logbook = make_logbook(elogy_client)
    in_entry, entry = make_entry(elogy_client, logbook)

    # change the title
    new_in_entry = {**in_entry, "title": "New title", "revision_n": 0}
    out_entry = decode_response(
        elogy_client.put("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook, entry=entry),
                         data=new_in_entry))
    print(out_entry)
    assert out_entry["title"] == new_in_entry["title"]
    assert out_entry["content"] == new_in_entry["content"]
    assert out_entry["id"] == entry["id"]

    # verify that the new revision can be retrieved
    new_entry_version = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook, entry=entry)))
    assert new_entry_version == out_entry
    assert new_entry_version["revision_n"] == 1

    # verify that the original revision is available
    old_entry_version = decode_response(
        elogy_client.get(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/revisions/0"
            .format(logbook=logbook, entry=entry)))
    assert old_entry_version["title"] == in_entry["title"]
    assert old_entry_version["revision_n"] == 0

    revisions = decode_response(
        elogy_client.get(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/revisions/"
            .format(logbook=logbook, entry=entry)))
    print("revisions", revisions)


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
        elogy_client.post(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
            .format(logbook=logbook, entry=entry),
            data=in_followup))

    # get the followup directly
    out_followup = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{followup[id]}/"
                         .format(logbook=logbook, followup=followup)))
    assert out_followup["id"] == followup["id"]

    # read the parent entry back
    out_entry = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{entry[id]}/"
                         .format(logbook=logbook, entry=entry)))

    assert out_entry["followups"][0]["id"] == followup["id"]

    # check that we get the parent when asking for the whole "thread"
    out_thread = decode_response(
        elogy_client.get("/api/logbooks/{logbook[id]}/entries/{followup[id]}/"
                         .format(logbook=logbook, followup=followup),
                         data={"thread": True}))
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
                         data=new_in_entry))

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
            environ_base={'REMOTE_ADDR': IP}))

    assert lock["owned_by_ip"] == IP

    # verify that the entry is locked
    get_lock = decode_response(
        elogy_client.get(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry)))
    assert get_lock["id"] == lock["id"]

    # acquire the lock again from the same host
    lock_again = decode_response(
        elogy_client.post(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry),
            environ_base={'REMOTE_ADDR': IP}))

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
            environ_base={'REMOTE_ADDR': IP}))

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
            data={"lock_id": lock["id"]}))
    assert cancelled_lock["cancelled_at"] is not None

    # acquire the lock from the other host
    other_lock2 = decode_response(
        elogy_client.post(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry),
            environ_base={'REMOTE_ADDR': OTHER_IP}))
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
            environ_base={'REMOTE_ADDR': IP}))

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
        elogy_client.post(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry),
            data=dict(steal=True),
            environ_base={'REMOTE_ADDR': OTHER_IP}))
    assert stolen_lock["id"] != lock["id"]

    # verify that the entry lock has changed
    lock2 = decode_response(
        elogy_client.get(
            "/api/logbooks/{logbook[id]}/entries/{entry[id]}/lock"
            .format(logbook=logbook, entry=entry)))
    assert lock2["id"] == stolen_lock["id"]
    assert lock2["owned_by_ip"] == OTHER_IP
