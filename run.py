"""
A simple HTTP "REST like" API for creating and accessing logbooks.
"""

from dateutil.parser import parse as parse_timestamp

from flask import Flask, request, jsonify, make_response, render_template
from flask_restful import Resource, Api
from peewee import OperationalError, fn
from playhouse.shortcuts import model_to_dict, dict_to_model

from app.db import (db,
                    Logbook, LogbookRevision,
                    Entry, EntryRevision)
from app.api import LogbooksResource, EntriesResource, SearchResource
from app.entries import entries
from app.logbooks import logbooks
from app.attachments import attachments


app = Flask(__name__)
app.config.from_pyfile('config.py')
api = Api(app)
app.register_blueprint(entries, url_prefix="/entries")
app.register_blueprint(logbooks, url_prefix="/logbooks")
app.register_blueprint(attachments, url_prefix="/attachments")


db.init_app(app)
try:
    # make sure the database tables exist
    db.database.create_tables([
        Logbook, LogbookRevision,
        Entry, EntryRevision,
        # EntrySearch,
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
    return render_template("index.html", logbooks=logbooks,
                           title=app.config.get("TITLE", ""))


@app.route("/mobile")
def get_index_mobile():
    logbooks = Logbook.select().where(Logbook.parent == None)
    return render_template("index_mobile.html", logbooks=logbooks,
                           title=app.config.get("TITLE", ""))


if __name__ == '__main__':
    app.run()
