TITLE = "elogy"

SECRET_KEY = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'  # !!!Change this!!!

DEBUG = True  # !!!Change this to False for production use!!!

# The name of the database file
DATABASE = "elogy.db"  # !!!Do not use /tmp for anything beyond testing!!!

# The folder where all uploaded files will be stored.
UPLOAD_FOLDER = '/tmp/elogy'  # !!!Again, /tmp is a bad choice!!!

# Optional LDAP config. Used to autocomplete author names.
# Requires the "pyldap" package. If not set, elogy will try
# to fall back to looking up users through the local system.
#LDAP_SERVER = "srv-ldap-2.maxiv.lu.se"
#LDAP_BASEDN = "dc=maxlab,dc=lu,dc=se"


# Callbacks for various events

def new_entry(entry):
    "Gets run whenever a new entry has been created"

    # 'entry' is the entry we just created, so it contains all the
    # data, e.g. title, authors, content, attributes and so on.
    # It's *not* the actual db model object, it's serialized
    # into a dict (same format as the JSON api). We don't want user
    # scripts to accidentally modify the database...

    # It's OK to do potentially slow stuff here such as network
    # calls, since actions are run in a thread. But make sure it
    # terminates sooner or later or you will have a resource leak!

    # Some example actions:
    if "Mailto" in entry["attributes"]:
        # Send an email to entry.attributes["Mailto"],
        # perhaps using the "smtplib" module?
        pass
    if "Ticket" in entry["attributes"]:
        # Create a ticket in your ticket system
        pass


ACTIONS = {
    "new_entry": new_entry,
    "edit_entry": None,
    "new_logbook": None,
    "edit_logbook": None
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
