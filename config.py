TITLE = "elogy"

SECRET_KEY = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

DEBUG = True  # change this to False for production use!

DATABASE = "/tmp/test.db"  # name of the database file

# the folder where all uploaded images will be stored.
UPLOAD_FOLDER = '/tmp/attachments'

# Currently we only care about images.
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'svg', 'bmp'])

# Don't change anything below this line unless you know what you're doing!
# ------------------------------------------------------------------------

DATABASE = {
    # Note: Currently *only* tested with sqlite!
    "name": DATABASE,
    "engine": "playhouse.sqlite_ext.SqliteExtDatabase",
    "threadlocals": True,
}
