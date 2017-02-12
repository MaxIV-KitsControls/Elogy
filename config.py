TITLE = "elogy"

SECRET_KEY = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'  # !!!Change this!!!

DEBUG = True  # !!!Change this to False for production use!!!

# The name of the database file
DATABASE = "/tmp/test.db"  # !!!Do not use /tmp for anything but testing!!!

# The folder where all uploaded files will be stored.
UPLOAD_FOLDER = '/tmp/attachments'  # !!!Again, /tmp is a bad choice!!!


# Here you can define what to do when things happen, e.g. a new entry
# has been created. You'll get the relevant, final db object.
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
