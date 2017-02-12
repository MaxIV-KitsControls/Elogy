TITLE = "elogy"

SECRET_KEY = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'  # !!!Change this!!!

DEBUG = True  # !!!Change this to False for production use!!!

# The name of the database file
DATABASE = "/tmp/elogy.db"  # !!!Do not use /tmp for anything beyond testing!!!

# The folder where all uploaded files will be stored.
UPLOAD_FOLDER = '/tmp/elogy'  # !!!Again, /tmp is a bad choice!!!


# Callbacks for various signals

def new_entry(entry):
    print("new_entry", entry.id, entry.title)


ACTIONS = {
    "new_entry": new_entry,
    "edit_logbook": None,
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
}
