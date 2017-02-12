"""
After an import with insert_stuff.py, finds old ELOG links in the
database and converts them to new URLs. Operates directly on the
DB file, so back it up before trying.
"""

import os
import re

from lxml import html


def update_bad_links(db, url):
    QUERY = "SELECT id, content FROM entry WHERE content LIKE ?"
    for entry_id, content in db.execute(QUERY, ["%{}%".format(url)]):
        print("=" * 40)
        print("entry ID:", entry_id)
        doc = html.document_fromstring(content)
        for element in doc.xpath("//*[@href]"):
            print(element.attrib["href"])
            results = re.search(os.path.join(url, '(.*)'), element.attrib["href"])
            if results:
                elog_url, = results.groups()
                print("elog_url", elog_url)
                rows = db.execute("SELECT id FROM entry WHERE json_extract(entry.metadata, '$.original_elog_url') = ?", [elog_url])
                result = rows.fetchone()
                if result:
                    linked_entry_id, = result
                    old_url = str(element.attrib["href"])
                    new_url = "/entries/{}".format(linked_entry_id)
                    print("\t", old_url, new_url)
                    db.execute(
                        "UPDATE entry SET content = replace(content, ?, ?) WHERE id = ?",
                        [old_url, new_url, entry_id])
                else:
                    print("Sorry, could not find new url!")


if __name__ == "__main__":

    import sys
    import sqlite3

    # List of base URLs to look for.
    OLD_URLS = ["elog.maxiv.lu.se", "control.maxiv.lu.se/elog"]

    conn = sqlite3.connect(sys.argv[1])
    for url in OLD_URLS:
        update_bad_links(conn, url)
    conn.commit()
