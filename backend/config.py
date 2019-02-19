import os
import re

TITLE = os.getenv('ELOGY_TITLE', 'elogy')

BASEURL = os.getenv('ELOGY_URL', 'https://elogy.maxiv.lu.se')

DEBUG = bool(os.getenv('ELOGY_DEBUG', 1))  # !!!Change this to False for production use!!!

# The name of the database file
DATABASE = os.getenv('ELOGY_DATABASE', 'elogy.db')  # !!!Do not use /tmp for anything beyond testing!!!


# The secret used by python in sessions
SECRET = os.getenv('ELOGY_SECRET', 'MW3sr3ctkmRvagBE')  

# The folder where all uploaded files will be stored.
UPLOAD_FOLDER = os.getenv('ELOGY_UPLOAD_FOLDER', '/tmp/elogy')  # !!!Again, /tmp is a bad choice!!!

# Optional LDAP config. Used to autocomplete author names.
# Requires the "pyldap" package. If not set, elogy will try
# to fall back to looking up users through the local system.
LDAP_SERVER = os.getenv("ELOGY_LDAP_SERVER", "")
LDAP_BASEDN = os.getenv("ELOGY_LDAP_BASEDN", "")
LDAP_BIND_USERNAME = os.getenv("ELOGY_LDAP_BIND_USERNAME", "")
LDAP_BIND_PASSWORD = os.getenv("ELOGY_LDAP_BIND_PASSWORD", "")

# Callbacks for various events

def new_entry(data):
    "Gets run whenever a new entry has been created"

    entry = data["entry"]

    # 'entry' is the entry we just created, so it contains all the
    # data, e.g. title, authors, content, attributes and so on.
    # It's *not* the actual db model object, it's serialized
    # into a dict (same format as the JSON api). We don't want user
    # scripts to accidentally modify the database...

    # Should be OK to do potentially slow stuff here such as network
    # calls, since actions are run in a thread. But make sure it
    # terminates sooner or later or you will have a resource leak!

    # Some example actions:
    if "Mailto" in entry["attributes"]:

        # Send an email to the address(es) given in the "Mailto" attribute

        # TODO: inline images aren't displayed since they are just
        #       relative links. Might be a good idea to inline them.
        # TODO: shouldn't assume messages are HTML
        # TODO: include entry authorship information?

        import logging
        from smtplib import SMTP
        from email.mime.text import MIMEText
        if "Mailfrom" in entry["attributes"]:
            fromaddr = entry["attributes"]["Mailfrom"]
        else:
            fromaddr = "elogy@maxiv.lu.se"

        toaddrs = entry["attributes"]["Mailto"]
        linkToText = 'Sent from Elogy, original post can be found at:'
        linkToEntry = BASEURL + '/logbooks/' + str(entry["logbook"]["id"]) + '/entries/' + str(entry["id"])
        content = "<html> {} <br> {} </html>".format(entry["content"], linkToText + linkToEntry)
        content = re.sub('src="', 'src="' + BASEURL, content)
        content = re.sub('href="', 'href="' + BASEURL, content)
        message = MIMEText(content, "html")
        message["Subject"] = entry["title"]
        message["From"] = fromaddr
        message["To"] = toaddrs
        with SMTP("smtp.maxiv.lu.se", 25) as smtp:
            logging.info(smtp.send_message(message))

    if "Ticket" in entry["attributes"]:
        # Create a ticket in your ticket system
        pass


def edit_logbook(data):
    print("edit_logbook", data)


ACTIONS = {
    "new_entry": new_entry,
    "edit_entry": None,
    "new_logbook": None,
    "edit_logbook": None  # edit_logbook
}


# Don't change anything below this line unless you know what you're doing!
# ------------------------------------------------------------------------

DATABASE = {
    # Note: Currently *only* works with sqlite!
    "name": DATABASE,
    "engine": "playhouse.sqlite_ext.SqliteExtDatabase",
    "threadlocals": True,
    "journal_mode": "WAL"
}
