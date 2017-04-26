"""A quick and dirty script to import data from elog logbooks. Tries
to adapt logbooks, attributes, attachments etc to the elogy data model.

Not thoroughly tested, does not support all elog features.

To run it, point it at a running elogy instance, an existing elog
config file and corresponding logbook directory, like so:

$ python3 import_elog.py localhost:8000 /etc/elogd.cfg /var/lib/elog/logbooks/

If you have many logbooks or lots of attachments this can take some
minutes to complete. There is currently no way to filter which logbooks
to import.

Known issues:

- Only works with the old "flat" ELOG file structure. Newer versions
  (AFAIK) stores stuff in a nested date-based tree which would require
  some changes to this script.

- Links to other logbook posts will be broken, since the urls are
  different and entry IDs will change. For now, the old URLS are kept
  in the metadata ("original_elog_url"), so a post-processing step
  should be able to correct the links.  (see "fix_elog_links.py")

- This also means that replies to entries may be broken. Maybe
  a more serious effort to insert entries in chronological order
  would fix that (now uses file timestamps, but that will not
  be correct if entries are edited later.)

- Thumbnailing some image attachments fails (e.g. GIF, TIFF).
  Example: 1486734443-130903_084110_BF3_self_triggered_2013-09-02.gif

- No error handling.

"""

from glob import glob
import logging
import os
import time
import urllib

from dateutil.parser import parse as parse_time
from dateutil.tz import tzlocal
from lxml import html, etree


EXCLUDED_ATTRIBUTES = set(["last edited", "author", "subject"])


def import_logbook(create_logbook, create_entry, create_attachment,
                   config, name, attribute_config={}, attributes=[],
                   root_path=".", parent=None, logbooks={}):

    """Import logbooks and entries from an elog config"""

    print()
    print("---Importing toplevel logbook %s" % name)
    if parent:
        print("    (child of %s)" % parent)

    try:
        props = config["%s%s" % ("" if parent else "global ", name)]
        props = props or {}
    except KeyError:
        props = {}
    print("props", list(props.keys()))

    # attributes can be defined in a parent logbook and will
    # then be inherited to its children
    attribute_config = dict(**attribute_config)
    required = [
        a.strip().lower()
        for a in props.get("required attributes", "").split(",")
    ]
    if "required attributes" in props:
        required = set([
            a.strip()
            for a in props.get("required attributes").split(",")
        ])
    else:
        required = set()
    # print("Required attributes: %s" % ", ".join(required))
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
    # we need to update attributes that are now (re)configured
    attributes = [attribute_config[attr["name"].lower().strip()]
                  for attr in attributes]
    # Pick up attributes
    if "attributes" in props:
        for attr_name in props["attributes"].split(","):
            print(attr_name)
            generic_name = attr_name.strip().lower()
            if generic_name in EXCLUDED_ATTRIBUTES:
                continue
            if generic_name in attribute_config:
                attr = attribute_config[generic_name]
                #attr["name"] = name
                #attr["required"] = (name in required or
                #                    attr["required"])
            else:
                attr = {
                    "name": attr_name,
                    "type": "text",
                    "required": generic_name in required
                }
            attributes.append(attr)

    print("Attriutes", attributes)

    # create a new logbook
    result = create_logbook(name, parent, props.get("Comment"), attributes)
    logbook_id = result["logbook_id"]

    # find all entries
    logbooks[logbook_id] = name
    entries_dir = props.get("subdir", name)
    logbook_path = os.path.join(root_path, entries_dir)
    created_entries = {}
    for logfile in sorted(glob(os.path.join(logbook_path, "*.log")),
                          key=os.path.getmtime):
        try:
            entries = load_elog_file(logfile)
            for entry in entries:
                timestamp = parse_time(entry["date"])

                data = {
                    "logbook_id": logbook_id,
                    "created_at": str(timestamp),
                    "title": entry.get("subject"),
                    # "content": body,
                    "authors": [a.strip()
                                for a in entry.get("author", "").split(",")],
                    "content_type": ("text/html"
                                     if entry.get("encoding").upper() == "HTML"
                                     else "text/plain"),
                    "metadata": {
                        "original_elog_url": os.path.join(name, str(entry["mid"])).replace(" ", "+")
                    },
                    "attributes": {}
                }

                for attr in attributes:
                    value = entry.get(attr["name"].lower())
                    if value:
                        data["attributes"][attr["name"]] = value.strip()

                if "last edited" in entry:
                    try:
                        # This is a tricky one; it seems that elog
                        # saves the create time with timezone info,
                        # but the last change is missing the timezone.
                        # Since we want to store UTC timestamps, we'll
                        # just have to assume that the timezone is the
                        # local one (at the time of running this
                        # script...
                        data["last_changed_at"] = (
                            parse_time(entry["last edited"])
                            .replace(tzinfo=tzlocal())
                            .strftime('%Y-%m-%d %H:%M:%S.%f'))
                    except ValueError as e:
                        print("Could not parse change date", e)

                if "in reply to" in entry:
                    follows = int(entry["in reply to"])
                    if follows in created_entries:
                        data["follows"] = created_entries[follows]
                    else:
                        print("Could not find parent", follows)

                if "encoding" in entry:
                    if entry["encoding"].upper() == "HTML":
                        data["content_type"] = "text/html"
                    else:
                        data["content_type"] = "text/plain"

                if entry.get("body"):
                    # here we upload any image attachments in the post
                    data["content"], embedded = handle_img_tags(
                        create_attachment, entry["body"], timestamp,
                        logbook_path)
                    # body = entry["body"].decode("utf-8")
                    # embedded = []
                else:
                    data["content"] = None
                    embedded = []
                embedded = [e.replace("/", "_") for e in embedded]

                # and here we push the entry to the API
                result = create_entry(data)
                created_entries[entry["mid"]] = result["entry_id"]

                # upload any attachments that are not embedded images
                if entry.get("attachment"):
                    attachments = [
                        a.strip() for a in
                        entry["attachment"].split(",")
                    ]
                    print(set(attachments) - set(embedded))
                    # data["attachments"] = [
                    #     create_attachment(result["entry_id"],
                    #                       os.path.join(logbook_path,
                    #                                    attachment))
                    #     for attachment in attachments
                    #     if attachment not in embedded
                    # ]
                    for attachment in attachments:
                        create_attachment(result["entry_id"],
                                          os.path.join(logbook_path, attachment),
                                          embedded=False)

        except UnicodeDecodeError as e:
            print("Error parsing logfile %s" % logfile)
            print(e)
    children = None
    try:
        if parent:
            children = config.get("global", "Group %s" % name)
        else:
            children = config.get("global", "Top group %s" % name)
    except configparser.NoOptionError as e:
        print("No children of %s: %s" % (name, e))
    if children:
        # recurse into child logbooks, and so on
        children = [child.strip() for child in children.split(",")]
        for child in children:
            import_logbook(create_logbook, create_entry, create_attachment,
                           config, child, root_path=root_path,
                           attribute_config=attribute_config, attributes=attributes,
                           parent=logbook_id, logbooks=logbooks)


def load_elog_config(create_logbook, create_entries, filename):
    "Parse an elog config file"
    config = configparser.RawConfigParser()
    config.read(filename)
    logbooks = {}

    for key in config["global"]:
        if key.startswith["Top group "]:
            logbook_name = key[10:]
            create_logbook(create_logbook, create_entries, config,
                           logbook_name, logbooks=logbooks)


def load_elog_file(filename):
    "parse an elog .log file into separate entries"
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


def handle_img_tags(create_attachment, text, timestamp, directory):
    "Find all linked images in an entry, and upload them"
    embedded_attachments = []
    try:
        doc = html.document_fromstring(text)
    except etree.ParserError:
        return text.decode("utf-8"), embedded_attachments
    for element in doc.xpath("//*[@src]"):
        src = element.attrib['src'].split("?", 1)[0]
        if not src.startswith("data:"):
            embedded_attachments.append(src)
            filename = urllib.parse.unquote(src.replace("/", "_"))
            candidates = glob(os.path.join(directory, filename))
            if not candidates:
                print("no candidates found for", directory, src)
                continue
            if len(candidates) > 1:
                print("Multiple candidates for", src)
            src = element.attrib['src'] = create_attachment(0, candidates[0],
                                                            embedded=True)
            if element.getparent().tag == "a":
                element.getparent().attrib["href"] = src

    return (html.tostring(doc).decode("utf-8"), embedded_attachments)


def create_logbook(session, url, name, parent, description, attributes):
    "helper to upload a new logbook"
    return session.post(url,
                        json={"name": name,
                              "parent": parent or None,
                              "description": description,
                              "attributes": attributes}).json()


def create_entry(session, url, entry):
    "helper to upload an entry"
    return session.post(url.format(**entry), json=entry).json()


def create_attachment(session, url, entry_id, filename, embedded=False):
    "helper to upload an attachment"
    try:
        timestamp = time.ctime(os.path.getctime(filename))
        with open(filename, "rb") as f:
            data = dict(entry_id=entry_id, timestamp=timestamp)
            if embedded:
                data["embedded"] = True
            response = session.post(url, files={"attachment": f}, data=data)
            print(response)
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

    import configparser
    from functools import partial
    import sys
    from requests import Session

    host_port = sys.argv[1]
    elogd_config = sys.argv[2]
    logbook_path = sys.argv[3]
    logbooks = sys.argv[4:]

    s = Session()

    # create a new logbook through the API
    LOGBOOK_URL = "http://%s/api/logbooks/" % host_port
    ENTRY_URL = "http://%s/api/logbooks/{logbook_id}/entries" % host_port
    ATTACHMENT_URL = "http://%s/api/attachments/" % host_port

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
    logbook_ids = {}
    for logbook in top_logbooks:
        if not logbooks or logbook in logbooks:
            import_logbook(partial(create_logbook, s, LOGBOOK_URL),
                           partial(create_entry, s, ENTRY_URL),
                           partial(create_attachment, s, ATTACHMENT_URL),
                           config, logbook,
                           root_path=logbook_path, logbooks=logbook_ids)
