"""
A simple HTTP "REST like" API for creating and accessing logbooks.
"""

import datetime
import json

from flask import Flask, request, render_template, jsonify
from flask.json import JSONEncoder
import peewee
from playhouse.shortcuts import model_to_dict
from peewee import OperationalError

from app.db import (db,
                    Logbook, LogbookRevision,
                    Entry, EntryRevision, EntryLock,
                    Attachment)
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


app.json_encoder = CustomJSONEncoder

app.register_blueprint(entries, url_prefix="/entries")
app.register_blueprint(logbooks, url_prefix="/logbooks")
app.register_blueprint(attachments, url_prefix="/attachments")
app.register_blueprint(search, url_prefix="/search")


@app.template_filter()
def to_json(value):
    return json.dumps(value)


db.init_app(app)
try:
    # make sure the database tables exist
    db.database.create_tables([
        Logbook, LogbookRevision,
        Entry, EntryRevision, EntryLock,
        Attachment
    ])
except OperationalError:
    pass


@app.route("/")
def get_index():
    parameters = request.args
    parent = parameters.get("parent")
    if parent:
        parent_logbook = Logbook.get(Logbook.id == parent)
    else:
        parent_logbook = None
    logbooks = Logbook.select().where(Logbook.parent == parent)
    return render_template("index.jinja2",
                           parent=parent_logbook,
                           logbooks=logbooks,
                           title=app.config.get("TITLE", ""))


@app.route("/mobile")
def get_index_mobile():
    logbooks = Logbook.select().where(Logbook.parent == None)
    return render_template("index_mobile.jinja2", logbooks=logbooks,
                           title=app.config.get("TITLE", ""))


if __name__ == '__main__':
    app.run(host="0.0.0.0")
