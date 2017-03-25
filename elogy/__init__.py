"""
A simple HTTP "REST like" API for creating and accessing logbooks.
"""

import json

from flask import Flask, request, render_template
from peewee import OperationalError

from .db import (db,
                 Logbook, LogbookRevision,
                 Entry, EntryRevision, EntryLock,
                 Attachment)
from .entries import entries
from .logbooks import logbooks
from .attachments import attachments
from .search import search
from .utils import CustomJSONEncoder


app = Flask(__name__)
app.config.from_envvar('ELOGY_CONFIG_FILE')
app.json_encoder = CustomJSONEncoder

# most entry points are defined in "blueprints"
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
    "Serve the top level index that contains the whole thing"
    parameters = request.args
    parent = parameters.get("parent")
    if parent:
        parent_logbook = Logbook.get(Logbook.id == parent)
        logbooks = Logbook.select().where(Logbook.id == parent)
    else:
        parent_logbook = None
        logbooks = (Logbook.select()
                    .where(Logbook.parent == None)
                    .order_by(Logbook.name))
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
