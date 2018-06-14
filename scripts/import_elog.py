"""
This script attempts to import an ELOG installation to Elogy.

The process is
1. parse all logbooks from the config file
2. parse all posts via the logbook data
3. import the logbooks to elogy
4. import entries (with attachments)
6. done!

For each logbook and entry, we first check if they are already
imported (using some metadata properties) and if so, ignore them
unless they have been edited since then.

There are several weird cases where we either do an educated guess,
or just skip that particular logbook/entry/whatever. Hopefully the
output should give you some hints as to why.

There's no checking to see if a logbook is already present so
in that case you will end up with several logbooks of the same
name (which is fine in elogy).

Usage:

    $ python import_elog.py http://elogy-host /path/to/elogd.conf /path/to/elog/logbooks --logbook Logbook1 --logbook "Some other logbook" --logbook ParentLogbook/ChildLogbook --since 2017-08-10

Note that the (optional) names of logbooks to be imported must be the
full names of the logbooks in the config file, not the names of the
directories they are in! Logbook names are unique in elog, so it's
not necessary to give them as a "path". If none are given, all logbooks
in the config are imported.

The "--since" parameter tells the script to not care about entries
not created or edited since that timestamp. This is intended for the
case where you want to sync an elog instance to elogy by running a
script at regular intervals. This is probably not a great idea unless
needed for a limited transfer period, as it likely does not cover all
possible corner cases.

After running this script, you may also want to run "fix_elog_links.py" in
order to repair any links in entries to attachments or other entries. See
that script for more details
"""

from collections import OrderedDict
import configparser
from datetime import datetime
from glob import glob
from itertools import chain
import json
import logging
import os
import time
from uuid import uuid4
from urllib.parse import quote_plus

try:
    import bbcode
except ImportError:
    logging.warning("No bbcode module installed; won't try to convert ELCode entries!")
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

    if not name:
        # a logbook must have a name; something is wrong
        return

    # get configuration properties for the logbook
    logging.debug("parsing logbook '%s' in '%s'", name, parent)
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
    if "Required Attributes" in props:
        required = set([
            a.strip()
            for a in props.get("Required Attributes").split(",")
        ])
    else:
        required = set()

    # we'll copy parent's attribute config to children
    attribute_config = dict(**attribute_config)
    logging.debug("inheriting %d attributes", len(attribute_config))
    # read attribute options
    for key in props:
        if key.lower().startswith("options "):
            attribute = key.split(" ", 1)[1]
            options = [o.strip() for o in props[key].split(",")]
            attribute_config[attribute.lower().strip()] = {
                "name": attribute,
                "type": "option",
                "options": options,
                "required": attribute in required
            }

    # this is an (ordered) dict of attributes
    attributes = OrderedDict(
        (attr["name"].lower().strip(),
         attribute_config[attr["name"].lower().strip()])
         for attr in attributes.values())

    # Pick up new attributes, overriding inherited ones
    if "Attributes" in props:
        for attr_name in props["Attributes"].split(","):
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
            attributes[generic_name] = attr

    entries_dir = props.get("Subdir", name)

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
        "attributes": list(attributes.values()),
        "path": os.path.join(root_path, entries_dir),
        "parent": parent,
        "children": child_logbooks,
        "metadata": {
            "original_elog_name": name,
            "original_elog_path": os.path.join(root_path, entries_dir)
        }
    }
    return logbook_uuid


def get_entries(logbook, accumulator):
    "Parse all entries belonging to a given logbook"
    logbook_path = logbook["path"]
    logging.debug("parsing entries for logbook '%s'", logbook["name"])
    for logfile in sorted(glob(os.path.join(logbook_path, "**/*.log"),
                               recursive=True),
                          key=os.path.getmtime):
        try:
            entries = load_elog_file(logfile)
            for entry in entries:
                logging.debug("parsing entry %d in %s", entry["mid"], logbook["name"])
                timestamp = parse_time(entry["date"]).replace(tzinfo=tzlocal())
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
                        "original_elog_url": os.path.join(quote_plus(logbook["name"]),
                                                          str(entry["mid"]))
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
                        # Also, sometimes the "last edited" field is just
                        # a time, without a date. I don't know if this
                        # is a bug or not, but default to using the
                        # creation date in this case (what else?) :(
                        data["last_changed_at"] = (
                            parse_time(entry["last edited"], default=timestamp)
                            .replace(tzinfo=tzlocal()))

                    except ValueError as e:
                        # Sometimes the "last edited" field is just
                        # not a date at all, but a name or something,
                        # and sometimes it's a weird timestamp. In those
                        # cases we'll just ignore it, nothing else to
                        # do. This seems a little dangerous, as it's
                        # possible that the parser gets fooled and produces
                        # a nonsense timestamp, but I haven't seen it so far.
                        logging.warning("Could not parse change date '%s' in %s/%s: %s",
                                        entry["last edited"], logbook["name"], entry["mid"], e)

                # is this a reply to another entry ("followup")?
                if "in reply to" in entry:
                    logging.debug("found reply: %s -> %s", data["mid"], entry["in reply to"])
                    follows = int(entry["in reply to"])
                    if follows:
                        # sometimes, the field can be "0", which I
                        # guess means it's not a reply after all..?
                        data["in_reply_to"] = (logbook["uuid"], follows)

                # content
                if entry.get("body"):
                    content, content_type = process_body(entry["body"], entry["encoding"])
                    data["content"] = content
                    data["content_type"] = content_type

                # attachments
                attachment_path = os.path.dirname(logfile)
                if entry.get("attachment"):
                    attachments = [
                        os.path.join(attachment_path, a.strip()) for a in
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
            logging.warning("Malformed entry!? %s: %r", filename, e)
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
                              "attributes": logbook["attributes"],
                              "metadata": logbook["metadata"]}).json()


def create_entry(session, url, logbook_id, entry, entries):
    "helper to upload an entry"
    data = {
        "title": entry.get("title"),
        "authors": entry["authors"],
        "created_at": entry["created_at"].strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
        "content": entry.get("content"),
        "content_type": entry["content_type"],
        "attributes": entry.get("attributes"),
        "metadata": entry.get("metadata"),
    }
    if "last_changed_at" in entry:
        data["last_changed_at"] = entry["last_changed_at"].strftime('%Y-%m-%dT%H:%M:%S.%f%z')
    if "in_reply_to" in entry:
        try:
            follows = entries[entry["in_reply_to"]]
            url += "{}/".format(follows["id"])
        except KeyError:
            # We have to assume that the parent has been previouly imported
            # so we should be able to find it in elogy.
            # We construct an elog URL for the parent, which we can search
            # for in the elogy entry metadata.
            _, parent_mid = entry["in_reply_to"]
            logbook_name, mid = entry["metadata"]["original_elog_url"].split("/")
            parent_url = "{}/{}".format(logbook_name, parent_mid)
            metadata_filter = ("original_elog_url:{}"
                               .format(parent_url))
            get_url = url.format(logbook_id=logbook_id)
            results = s.get(get_url,
                            params={"metadata": metadata_filter}).json()["entries"]
            if len(results):
                url += "{}/".format(results[0]["id"])
            else:
                logging.error("could not find entry {} which {} is replying to!"
                              .format(entry["in_reply_to"], entry["mid"]))
                # Here there's not much we can do. Would it make more sense
                # to create the entry anyway, but not as a followup? I think
                # not, and this case should never really happen anyway.
                return
    entry_result = session.post(url.format(logbook_id=logbook_id), json=data)
    return entry_result


def update_entry(session, url, logbook_id, entry, entries, revision_n):
    "helper to update an entry"
    data = {
        "title": entry.get("title"),
        "authors": entry["authors"],
        "created_at": entry["created_at"].strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
        "content": entry.get("content"),
        "content_type": entry["content_type"],
        "attributes": entry.get("attributes"),
        "metadata": entry.get("metadata"),
        "revision_n": revision_n,
        "no_change_time": True
    }
    if "last_changed_at" in entry:
        data["last_changed_at"] = entry["last_changed_at"].strftime('%Y-%m-%dT%H:%M:%S.%f%z')
    entry_result = session.put(url.format(logbook_id=logbook_id), json=data)
    return entry_result


def create_attachment(session, url, filename, embedded=False):
    "helper to upload an attachment"
    try:
        # use the filesystem timestamp for the attachment
        timestamp = (datetime.fromtimestamp(os.path.getctime(filename))
                     .replace(tzinfo=tzlocal()))  # use local timestamp
        with open(filename, "rb") as f:
            data = dict(
                timestamp=timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                metadata=json.dumps({
                    "original_elog_filename": filename.rsplit("/", 1)[-1]
                })
            )
            if embedded:
                data["embedded"] = True
            response = session.post(url, files={"attachment": f}, data=data)
            if response.status_code == 200:
                return response.json()["location"]
            else:
                logging.error("failed to upload attachment '%s'", filename)
    except FileNotFoundError:
        logging.error("Could not find attachment '%s'", filename)


if __name__ == "__main__":

    import argparse
    from requests import Session

    parser = argparse.ArgumentParser(description='Import data from Elog to Elogy.')

    parser.add_argument("elogy_host", metavar="HOST", type=str,
                        help="Host:port of the target elogy instance")
    parser.add_argument("elogd_config", metavar="CONFIG", type=str,
                        help="Config file of the source Elog installation")
    parser.add_argument("elog_logbook_path", metavar="PATH", type=str,
                        help="Path to the directory where ELog logbooks are stored")
    parser.add_argument("-l", "--logbooks", type=str, nargs="+", default=[],
                        help="Specific logbook to import (by name)")
    parser.add_argument("-s", "--since", type=parse_time,
                        help="Only consider entries added/modified after this time")
    parser.add_argument("-i", "--ignore", action="store_false",
                        dest="check",  help="Don't care if logbooks and entries already exist")
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                        help="Print out debug information about what's going on")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    host_port = args.elogy_host
    elogd_config = args.elogd_config
    logbook_path = args.elog_logbook_path
    logbooks_to_import = set(chain(*(lb.split("/") for lb in args.logbooks)))

    s = Session()

    LOGBOOK_URL = "%s/api/logbooks/" % host_port
    ENTRY_URL = "%s/api/logbooks/{logbook_id}/entries/" % host_port
    ATTACHMENT_URL = "%s/api/logbooks/{logbook[id]}/entries/{entry[id]}/attachments/" % host_port

    config = configparser.RawConfigParser(strict=False)
    config.optionxform = str  # preserve key case
    config.read(elogd_config)

    sections = {
        s[7:].lower(): s[7:]
        for s in config.sections()
        if s.startswith("global ")
    }
    top_logbooks = [
        sections[key[10:].lower()] for key in config["global"]
        if key.startswith("Top group")
    ]

    # get all logbooks into a flat dict, keyed on name
    # I think logbook names are unique but to be sure
    # i assign them uuids.
    logbooks = {}
    logging.info("Importing logbooks %s", logbooks_to_import)

    for logbook in top_logbooks:
        if logbooks_to_import and logbook not in logbooks_to_import:
            continue
        get_logbook(config, logbook,
                    root_path=logbook_path, toplevel=True,
                    accumulator=logbooks, to_import=logbooks_to_import)
    logging.info("Got logbooks %r",
                 sorted(logbook["name"] for logbook in logbooks.values()))
    # get the entries in each logbook, also in a flat dict
    # keyed on (logbook_uuid, mid)
    entries = {}
    for lid, logbook in logbooks.items():
        get_entries(logbook, entries)

    # OK; now we're done parsing all the existing elog data. Now over
    # to actually importing it.

    imported_logbooks = {}

    logbook_tree = s.get(LOGBOOK_URL).json()["logbook"]
    # now we have a tree of all the logbooks currently in the system

    def flatten_logbooks(lbtree):
        "A generator that recursively yields logbooks from a tree"
        for lb in lbtree:
            # only care about logbooks that were originally imported from elog
            if "metadata" in lb and lb["metadata"]:
                if "original_elog_name" in lb["metadata"]:
                    yield lb["metadata"]["original_elog_name"], lb
            yield from flatten_logbooks(lb.get("children", []))

    existing_logbooks = dict(flatten_logbooks([logbook_tree]))

    def create_logbooks(lb, existing, parent=None):
        "Helper to recursively import logbooks"

        # if the logbook already exists (same name, logbook names are
        # unique in Elog) we don't create it
        # TODO but maybe update?
        if lb["name"] in existing_logbooks:
            logging.debug("Skipping existing logbook %s", lb["name"])
            imported_logbooks[lb["uuid"]] = existing[lb["name"]]
            return

        # skip logbooks already imported during this run (should never happen...)
        if lb["uuid"] in imported_logbooks:
            logging.warning("Skipping already imported logbook '%s'!?",
                            lb["name"])
            return

        # skip child logbooks whose parents have not yet been imported
        # (they will be imported after the parent is done)
        logging.debug("parent %r", lb.get("parent"))
        if (lb["parent"] is not None
                and lb["parent"] not in imported_logbooks):
            logging.debug("Deferring child logbook '%s'", lb["name"])
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
            logging.info("create %s", lid)
            create_logbooks(logbooks[lid], existing, parent=result["id"])

    logging.info("* importing logbooks *")
    # import all the toplevel logbooks
    for lid, logbook in logbooks.items():
        create_logbooks(logbook, existing_logbooks)

    def get_modification_time(entry):
        if entry.get("last_changed_at"):
            return entry["last_changed_at"]
        return entry["created_at"]

    if args.since:
        since = args.since.replace(tzinfo=tzlocal())
        entries = dict((k, e) for k, e in entries.items()
                       if get_modification_time(e) > since)

    logging.info("Number of entries to check: %d", len(entries))

    # sort entries by creation time. By inserting them in chronological order,
    # hopefully we can be sure that replies will work properly
    sorted_entries = OrderedDict(
        sorted(entries.items(),
               key=lambda t: t[1].get("created_at")))

    imported_entries = {}

    logging.info("* importing entries *")
    for (logbook_uuid, mid), entry in sorted_entries.items():

        logbook = logbooks[logbook_uuid]

        if logbook_uuid in imported_logbooks:
            logbook_result = imported_logbooks[logbook_uuid]
        else:
            logbook_result = existing_logbooks[logbook["name"]]
        # First check if the entry has been imported already.
        # for this we make use of the "metadata" inserted
        # with entries imported with this script.
        metadata_filter = ("original_elog_url:{}"
                           .format(entry["metadata"]["original_elog_url"]))
        get_url = ENTRY_URL.format(logbook_id=logbook_result["id"])
        results = s.get(get_url,
                        params={"metadata": metadata_filter}).json()["entries"]
        if results:
            # This means the entry has already been imported
            short_entry = results[0]
            existing_entry = s.get(get_url +
                                   str(short_entry["id"]) + "/").json()["entry"]
            if (parse_time(get_modification_time(existing_entry))
                    > get_modification_time(entry)):
                # entry has not been edited since import, ignore
                continue
            logging.info("updating entry %s/%d -> /logbooks/%d/entries/%d",
                         logbook_result["name"], mid,
                         logbook_result["id"], existing_entry["id"])
            update_url = "{}{}/".format(ENTRY_URL, existing_entry["id"])

            result = update_entry(s, update_url, logbook_result["id"],
                                  entry, imported_entries,
                                  revision_n=existing_entry["revision_n"])
            if result.status_code != 200:
                logging.info("failed to update entry {}/{} {}",
                             logbook_result["name"], mid, result.json())
        else:
            logging.info("creating entry %s/%d", logbook["name"], mid)
            result = create_entry(s, ENTRY_URL, logbook_result["id"],
                                  entry, imported_entries)
            if not result:
                logging.error("unable to create entry %s/%d!",
                              logbook_result["name"], mid)
            elif result.status_code == 200:
                result = result.json()["entry"]
                logging.info("successfully created entry %s/%d -> /logbooks/%d/entries/%d",
                             logbook_result["name"], mid,
                             logbook_result["id"], result["id"])
                for attachment in entry.get("attachments", []):
                    filename = os.path.join(logbook["path"], attachment)
                    create_attachment(
                        s, ATTACHMENT_URL.format(logbook=logbook_result,
                                                 entry=result),
                        filename)
                    logging.info("uploaded attachment %s to %s/%d -> %d",
                                 filename, logbook_result["name"], mid, result["id"])
                imported_entries[(logbook_uuid, mid)] = result
            else:
                logging.error("failed to create entry %s/%d %r",
                              logbook_result["name"], mid, result)

    # TODO: what about attachments?
