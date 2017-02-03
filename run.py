"""
A simple HTTP "REST like" API for creating and accessing logbooks.
"""

import datetime

from flask import Flask, render_template
from flask.json import JSONEncoder
from flask_restful import Api
import peewee
from playhouse.shortcuts import model_to_dict
from peewee import OperationalError

from app.db import (db,
                    Logbook, LogbookRevision,
                    Entry, EntryRevision, EntryLock)
from app.api import LogbooksResource, EntriesResource, SearchResource
from app.entries import entries
from app.logbooks import logbooks
from app.attachments import attachments
from app.search import search


app = Flask(__name__)
app.config.from_pyfile('config.py')


class CustomJSONEncoder(JSONEncoder):

    """JSON serializer for objects not serializable by default json code"""

    def default(self, obj):
        if isinstance(obj, datetime):
            serial = obj.timestamp()
            return serial
        elif isinstance(obj, peewee.Model):
            serial = model_to_dict(obj, recurse=False)
            return serial

        return JSONEncoder.default(self, obj)


app.config["RESTFUL_JSON"] = {'cls': CustomJSONEncoder}


api = Api(app)
app.register_blueprint(entries, url_prefix="/entries")
app.register_blueprint(logbooks, url_prefix="/logbooks")
app.register_blueprint(attachments, url_prefix="/attachments")
app.register_blueprint(search, url_prefix="/search")


db.init_app(app)
try:
    # make sure the database tables exist
    db.database.create_tables([
        Logbook, LogbookRevision,
        Entry, EntryRevision, EntryLock
    ])
except OperationalError:
    pass


api.add_resource(LogbooksResource,
                 '/api/logbooks', '/api/logbooks/<int:logbook_id>')
api.add_resource(EntriesResource,
                 '/api/entries', '/api/entries/<int:entry_id>')
api.add_resource(SearchResource,
                 '/api/search')


@app.route("/")
def get_index():
    logbooks = Logbook.select().where(Logbook.parent == None)
    return render_template("index.jinja2", logbooks=logbooks,
                           title=app.config.get("TITLE", ""))


@app.route("/mobile")
def get_index_mobile():
    logbooks = Logbook.select().where(Logbook.parent == None)
    return render_template("index_mobile.jinja2", logbooks=logbooks,
                           title=app.config.get("TITLE", ""))


if __name__ == '__main__':
    app.run(host="0.0.0.0")
