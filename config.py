SECRET_KEY = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

DEBUG = True  # change this to False for production use!

DATABASE = {
    # Note: Currently *only* tested with sqlite!
    "name": "test.db",  # name of the database file
    "engine": "playhouse.sqlite_ext.SqliteExtDatabase"
}

# the folder where all uploaded images will be stored.
UPLOAD_FOLDER = 'attachments'

WELCOME_MESSAGE = """
<p>Welcome to the web logbooks at SHOG labs!</p>
<p>There are currently three main projects here, each with a corresopnding logbook (see below). Feel free to access them, but please remember the confidentiality rules (Section 14, paragraphs 45-189 in the Manual).</p>

<p><i>Happy researching!</i></p>
"""

# Don't change anything below this line unless you know what you're doing!
# ------------------------------------------------------------------------

from datetime import datetime
from flask.json import JSONEncoder


class CustomJSONEncoder(JSONEncoder):

    def default(self, obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, datetime):
            serial = obj.timestamp()
            return serial
        return JSONEncoder.default(self, obj)


RESTFUL_JSON = {'cls': CustomJSONEncoder}
