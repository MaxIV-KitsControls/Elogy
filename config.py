TITLE = "elogy"

SECRET_KEY = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'  # !!!Change this!!!

DEBUG = False  # !!!Change this to False for production use!!!

# The name of the database file
DATABASE = "elogy.db"  # !!!Do not use /tmp for anything beyond testing!!!

# The folder where all uploaded files will be stored.
UPLOAD_FOLDER = '/tmp/elogy'  # !!!Again, /tmp is a bad choice!!!


# Callbacks for various events

def new_entry(entry):
    "Gets run whenever a new entry is created"
    # 'entry' is the Entry instance just created, so it contains
    # all the data about the post, e.g. entry.title, entry.authors,
    # entry.content and so on.

    # Some example actions:
    if "Mailto" in entry.attributes:
        # Send an email to entry.attributes["Mailto"],
        # perhaps using the "smtplib" module?
        pass
    if "Ticket" in entry.attributes:
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
