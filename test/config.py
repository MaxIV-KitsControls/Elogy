# This is a config file for testing purposes, it creates a temporary
# file for the database.

from tempfile import NamedTemporaryFile

TITLE = "elogy"

SECRET_KEY = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

DEBUG = False

# The name of the database file
with NamedTemporaryFile(delete=False) as f:
    DATABASE = f.name

# The folder where all uploaded files will be stored.
UPLOAD_FOLDER = '/tmp/test_elogy'


# Don't change anything below this line unless you know what you're doing!
# ------------------------------------------------------------------------

DATABASE = {
    # Note: Currently *only* works with sqlite!
    "name": DATABASE,
    "engine": "playhouse.sqlite_ext.SqliteExtDatabase",
    "threadlocals": True,
    "journal_mode": "WAL"
}
