"""
This script attempts to import an ELOG installation to Elogy.

The process is
1. parse all logbooks from the config file
2. parse all posts via the logbook data
3. import the logbooks to elogy
4. import entries (with attachments)
6. done!

There are several weird cases where we either do an educated guess,
or just skip that particular logbook/entry/whatever.

Usage:

$ python import_elog.py http://elogy-host /path/to/elogd.conf /path/to/elog/logbooks Logbook2 Parent/Logbook2

After this is done, you may also want to run "fix_elog_links.py"

"""

from collections import OrderedDict
import configparser
from glob import glob
import json
import logging
import os
import time
from uuid import uuid4

try:
    import bbcode
except ImportError:
    print("No bbcode module installed; won't try to convert ELCode entries!")
    bbcode = None
from dateutil.parser import parse as parse_time
from dateutil.tz import tzlocal


# elog treats some special values as attributes, elogy has
# specific handling for these so we won't treat them as
# attributes.
EXCLUDED_ATTRIBUTES = set(["last edited", "author", "subject"])


def get_logbook(config, name, parent=None,
                attribute_config={}, attributes={},
                root_path=".", toplevel=False, accumulator={},
                to_import=None):

    # get configuration properties for the logbook
    logging.info("parsing logbook '%s'", name)
    if to_import and name not in to_import:
        return
    try:
        if toplevel:
            props = config["global {}".format(name)] or {}
        else:
            props = config[name] or {}
    except KeyError:
        props = {}

    # check for required attributes
    if "required attributes" in props:
        required = set([
            a.strip()
            for a in props.get("required attributes").split(",")
        ])
    else:
        required = set()

    # we'll copy parent's attribute config to children
    attribute_config = dict(**attribute_config)
    logging.debug("inheriting %d attributes", len(attribute_config))
    # read attribute options
    for key in props:
        if key.startswith("options "):
            attribute = key.split(" ", 1)[1]
            options = [o.strip() for o in props[key].split(",")]
            attribute_config[attribute] = {
                "name": attribute,
                "type": "option",
                "options": options,
                "required": attribute in required
            }
    # override attributes that are now (re)configured
    attributes = [attribute_config[attr["name"].lower().strip()]
                  for attr in attributes]

    # Pick up attributes
    if "attributes" in props:
        for attr_name in props["attributes"].split(","):
            logging.debug("parsing attribute %s", attr_name)
            generic_name = attr_name.strip().lower()
            if generic_name in EXCLUDED_ATTRIBUTES:
                continue
            if generic_name in attribute_config:
                attr = attribute_config[generic_name]
            else:
                attr = {
                    "name": attr_name,
                    "type": "text",
                    "required": generic_name in required
                }
            attributes.append(attr)

    entries_dir = props.get("subdir", name)

    try:
        if toplevel:
            children = config.get("global", "Top group %s" % name)
        else:
            children = config.get("global", "Group %s" % name)
    except configparser.NoOptionError:
        children = None
    child_logbooks = []
    logbook_uuid = str(uuid4())
    if children:
        # recurse into child logbooks, and so on
        children = [child.strip() for child in children.split(",")]
        for child in children:
            lid = get_logbook(config, child, root_path=root_path,
                              attribute_config=attribute_config,
                              attributes=attributes, parent=logbook_uuid,
                              toplevel=False, accumulator=accumulator,
                              to_import=to_import)
            if lid is not None:
                child_logbooks.append(lid)

    accumulator[logbook_uuid] = {
        "uuid": logbook_uuid,
        "name": name,
        "description": None,
        "attributes": attributes,
        "path": os.path.join(root_path, entries_dir),
        "parent": parent,
        "children": child_logbooks
    }
    return logbook_uuid


def get_entries(logbook, accumulator):
    "Parse all entries belonging to a given logbook"
    logbook_path = logbook["path"]
    logging.info("parsing entries for logbook '%s'", logbook["name"])
    for logfile in sorted(glob(os.path.join(logbook_path, "*.log")),
                          key=os.path.getmtime):
        try:
            entries = load_elog_file(logfile)
            for entry in entries:
                logging.debug("parsing entry %d in %s", entry["mid"], logbook["name"])
                timestamp = parse_time(entry["date"])

                data = {
                    "mid": entry["mid"],
                    "logbook_uuid": logbook["uuid"],
                    "logbook_name": logbook["name"],
                    "created_at": timestamp,
                    "title": entry.get("subject"),
                    "authors": [{"login": None,  # TODO: somehow guess logins..?
                                 "name": a.strip()}
                                for a in entry.get("author", "").split(",")],
                    "metadata": {
                        "original_elog_url": os.path.join(
                            logbook["name"], str(entry["mid"])).replace(" ", "+")
                    },
                    "attributes": {}
                }
                for attr in logbook["attributes"]:
                    value = entry.get(attr["name"].lower())
                    if value:
                        data["attributes"][attr["name"]] = value.strip()

                if "last edited" in entry:
                    try:
                        # This is a tricky one; it seems that elog
                        # saves the create time with timezone info,
                        # but the last change is missing the timezone.
                        # We'll just assume that the timezone is the
                        # same as the local one when this script runs.
                        data["last_changed_at"] = (
                            parse_time(entry["last edited"])
                            .replace(tzinfo=tzlocal()))

                    except ValueError as e:
                        # Sometimes the "last_edited" field is just
                        # not a date at all, but a name or something,
                        # and sometimes it's a weird timestam In those
                        # cases we'll just ignore it, nothing else to
                        # do.
                        logging.warning("Could not parse change date '%s' in %s/%s: %s",
                                        entry["last edited"], logbook["name"], entry["mid"], e)

                if "in reply to" in entry:
                    logging.debug("found reply: %s -> %s", data["mid"], entry["in reply to"])
                    follows = int(entry["in reply to"])
                    if follows:
                        # sometimes, the field can be "0", which I
                        # guess means it's not a reply after all..?
                        data["in_reply_to"] = (logbook["uuid"], follows)

                if entry.get("body"):
                    content, content_type = process_body(entry["body"], entry["encoding"])
                    data["content"] = content
                    data["content_type"] = content_type

                if entry.get("attachment"):
                    attachments = [
                        a.strip() for a in
                        entry["attachment"].split(",")
                    ]
                    data["attachments"] = attachments
                accumulator[(logbook["uuid"], entry["mid"])] = data
        except UnicodeDecodeError as e:
            logging.warning("error parsing logfile %s: %s", (logfile, e))


def load_elog_file(filename):
    "parse an elog .log file into separate entries"

    logging.debug("parsing logfile '%s'", filename)

    with open(filename, encoding="ISO-8859-1") as f:
        content = f.read()

    entries = []
    for entry_text in content.split("$@MID@$:"):
        if not entry_text:
            continue
        entry = {}
        try:
            header, body = entry_text.split("=" * 40, 1)
        except ValueError as e:
            print("Malformed entry!?", e)
            print(entry)
            continue
        header_lines = header.split("\n")
        mid = int(header_lines[0].strip())
        for line in header_lines[1:]:
            try:
                key, value = line.split(":", 1)
                if value.strip():
                    entry[key.lower()] = value.strip()
            except ValueError:
                pass
        entry["body"] = body.encode("utf-8")
        entry["mid"] = mid
        entries.append(entry)

    return entries


def process_body(body, encoding):
    "Do some massaging of the raw body, depending on encoding"
    if encoding.lower() == "html":
        return body.decode("utf-8"), "text/html; charset=utf-8"
    if encoding.lower() == "plain":
        return body.decode("utf-8"), "text/plain; charset=utf-8"
    if encoding.lower() == "elcode":
        if bbcode:
            return (bbcode.render_html(body.decode("utf-8")),
                    "text/html; charset=utf-8")
        else:
            return body.decode("utf-8"), "text/plain; charset=utf-8"


def create_logbook(session, url, logbook):
    "helper to upload a new logbook"
    return session.post(url,
                        json={"name": logbook["name"],
                              "description": logbook["description"],
                              "attributes": logbook["attributes"]}).json()


def create_entry(session, url, logbook_id, entry, entries):
    "helper to upload an entry"
    data = {
        "title": entry.get("title"),
        "authors": entry["authors"],
        "created_at": entry["created_at"].strftime('%Y-%m-%d %H:%M:%S.%f %z'),
        "content": entry.get("content"),
        "content_type": entry["content_type"],
        "attributes": entry.get("attributes"),
        "metadata": entry.get("metadata"),
    }
    if "last_changed_at" in entry:
        data["last_changed_at"] = entry["last_changed_at"].strftime('%Y-%m-%d %H:%M:%S.%f %z')
    if "in_reply_to" in entry:
        try:
            follows = entries[entry["in_reply_to"]]
            url += "{}/".format(follows["id"])
        except KeyError:
            logging.warning("could not find entry {} which {} is replying to!"
                            .format(entry["in_reply_to"], entry["mid"]))

    entry_result = session.post(url.format(logbook_id=logbook_id), json=data)
    return entry_result


def create_attachment(session, url, filename, embedded=False):
    "helper to upload an attachment"
    try:
        print(filename)
        timestamp = time.ctime(os.path.getctime(filename))
        with open(filename, "rb") as f:
            data = dict(timestamp=timestamp)
            if embedded:
                data["embedded"] = True
            data["metadata"] = json.dumps({
                "original_elog_filename": filename.rsplit("/", 1)[-1]
            })
            response = session.post(url, files={"attachment": f}, data=data)
            if response.status_code == 200:
                return response.json()["location"]
            else:
                print("failed to upload", filename)
    except FileNotFoundError:
        print("Could not find attachment", filename)


if __name__ == "__main__":

    # Argument 1 is the host:port of the logbook server to post to
    # Argument 2 is the name of a elogd config file to import
    # Argument 3 is the base path where to look for logbook files
    # Further arguments should be names of the toplevel logbooks to
    # import. If none are given, imports all logbooks it finds in the config.

    import sys
    from requests import Session

    logging.basicConfig(level=logging.INFO)

    host_port = sys.argv[1]
    elogd_config = sys.argv[2]
    logbook_path = sys.argv[3]
    logbooks_to_import = sum((lb.split("/") for lb in sys.argv[4:]), [])
    print("logbooks to import", logbooks_to_import)

    s = Session()

    # create a new logbook through the API
    LOGBOOK_URL = "http://%s/api/logbooks/" % host_port
    ENTRY_URL = "http://%s/api/logbooks/{logbook_id}/entries/" % host_port
    ATTACHMENT_URL = "http://%s/api/logbooks/{logbook[id]}/entries/{entry[id]}/attachments/" % host_port

    config = configparser.RawConfigParser(strict=False)
    config.read(elogd_config)

    sections = {
        s[7:].lower(): s[7:]
        for s in config.sections()
        if s.startswith("global ")
    }
    top_logbooks = [
        sections[key[10:]] for key in config["global"]
        if key.startswith("top group")
    ]

    # get all logbooks into a flat dict, keyed on name
    # I think logbook names are unique but to be sure
    # i assign them uuids.
    logbooks = {}
    for logbook in top_logbooks:
        # if logbooks_to_import and logbook not in logbooks_to_import:
        #     continue
        get_logbook(config, logbook,
                    root_path=logbook_path, toplevel=True,
                    accumulator=logbooks, to_import=logbooks_to_import)
    # get the entries in each logbook, also in a flat dict
    # keyed on (logbook_uuid, mid)
    entries = {}
    for lid, logbook in logbooks.items():
        get_entries(logbook, entries)

    # OK; now we're done parsing all the existing elog data. Now over
    # to actually importing it.

    imported_logbooks = {}

    def create_logbooks(lb, parent=None):
        "Helper to recursively import logbooks"
        # skip logbooks already imported (should never happen...)
        if lb["uuid"] in imported_logbooks:
            return
        # skip child logbooks whose parents have not been imported
        # (they will be imported after the parent is done)
        if lb["parent"] is not None and lb["parent"] not in imported_logbooks:
            return

        if parent is not None:
            url = LOGBOOK_URL + "{}/".format(parent)
        else:
            url = LOGBOOK_URL
        result = create_logbook(s, url, lb)
        if result is None:
            return
        result = result["logbook"]
        imported_logbooks[lb["uuid"]] = result
        for lid in lb["children"]:
            create_logbooks(logbooks[lid], parent=result["id"])

    logging.info("importing logbooks")
    # import all the toplevel logbooks
    for lid, logbook in logbooks.items():
        create_logbooks(logbook)

    # sort entries by creation time. By inserting them in chronological order,
    # hopefully we can be sure that replies will work properly
    sorted_entries = OrderedDict(sorted(entries.items(),
                                        key=lambda t: t[1]["created_at"]))

    imported_entries = {}

    logging.info("importing entries")
    for (logbook_uuid, mid), entry in sorted_entries.items():
        logbook_result = imported_logbooks[logbook_uuid]
        logbook = logbooks[logbook_uuid]
        result = create_entry(s, ENTRY_URL, logbook_result["id"],
                              entry, imported_entries)
        if result.status_code == 200:
            result = result.json()["entry"]
            for attachment in entry.get("attachments", []):
                filename = os.path.join(logbook["path"], attachment)
                create_attachment(
                    s, ATTACHMENT_URL.format(logbook=logbook_result,
                                             entry=result),
                    filename)
            imported_entries[(logbook_uuid, mid)] = result

    # TO CONSIDER
    # + How do we make this script idempotent?
    #   The whole parsing step takes only a few seconds
    #   so it can be done often. If we just sort by descending
    #   creation date we could find the first entry that already
    #   exists and then start from the next..?
    #   I guess logbook changes will be harder. But they are
    #   infrequent and can only be done by KITS.
