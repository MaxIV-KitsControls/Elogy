from functools import partial

from dateutil.parser import parse
from flask import Flask, request, jsonify, make_response
from flask_restful import Resource, Api
from peewee import OperationalError, fn
from playhouse.shortcuts import model_to_dict, dict_to_model


from app.db import (db,
                    Logbook, LogbookRevision,
                    Entry, EntryRevision)
from app.entries import handle_img_tags


class LogbooksResource(Resource):

    def get(self, logbook_id=None):
        "Retrieve a logbook"
        if logbook_id:
            logbook = Logbook.get(Logbook.id == logbook_id)
            return model_to_dict(logbook, recurse=False,
                                 extra_attrs=["children", "entry_histogram"])
        parent = request.args.get("parent")
        if parent:
            parent = int(parent)
        logbooks = (Logbook.select()
                    .where(Logbook.parent == parent))
        for logbook in logbooks:
            print(logbook.name, logbook._data.get("parent"))
        return list(map(partial(model_to_dict, recurse=False), logbooks))

    def post(self):
        "Create a new logbook"
        logbook = dict_to_model(Logbook, request.json)
        logbook.save()
        return {"logbook": logbook.id}

    def put(self, logbook_id):
        "Update an existing logbook"
        logbook = Logbook.get(Logbook.id == logbook_id)
        change = logbook.make_change(request.json)
        return {"revision": change.id}


def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']


class EntriesResource(Resource):

    def get(self, entry_id=None):
        if entry_id:
            # requesting a single entry
            entry = Entry.get(Entry.id == entry_id)
            if request_wants_json():
                return model_to_dict(entry, backrefs=True,
                                     extra_attrs=["followups"])
            else:
                # just get the HTML content
                return make_response(entry.content)
        # requesting all entries for a given logbook
        if "logbook" in request.args:
            logbook_id = int(request.args["logbook"])
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
            # entries = (
            #     Entry.select(
            #         Entry.id, Entry.logbook,
            #         Entry.authors, Entry.title,
            #         Entry.created_at, Entry.last_changed_at,
            #     ).where((Entry.logbook_id == logbook_id) &
            #             (Entry.follows == None))
            #     .order_by(fn.coalesce(Entry.last_changed_at,
            #                           Entry.created_at).desc())
            #     .offset(offset)
            #     .limit(limit))
            logbook = Logbook.get(Logbook.id == logbook_id)
            entries = (logbook.get_entries()
                       .paginate(offset, limit))
            return list(map(partial(model_to_dict,
                                    exclude=[Entry.content],
                                    extra_attrs=["timestamp"],
                                    recurse=False), entries))

    def post(self):
        data = request.json
        data["content"], data["attachments"] = handle_img_tags(data["content"], parse(data["created_at"]))
        entry = dict_to_model(Entry, request.json)
        entry.save()
        return {"entry": entry.id}

    def put(self, entry_id):
        entry = Entry.get(Entry.id == entry_id)
        change = entry.make_change(request.json)
        return {"revision": change.id}


class SearchResource(Resource):

    def get(self):
        # if "content" in request.json:
        #     entries = EntrySearch.search(request.json["content"])
        #     return [entry.content for entry in entries]

        entries = Entry.select()
        if "content" in request.json:
            # really crude text search (probably slow too)
            content = request.json["content"]
            entries = entries.where(Entry.content.contains(content))
        if "attributes" in request.json:
            # exact matching on attribute values
            for attribute, value in request.json["attributes"].items():
                attr = fn.json_extract(Entry.attributes, "$." + attribute)
                entries = entries.where(attr == value)
        if "title" in request.json:
            title = request.json["title"]
            entries = entries.where(Entry.title.contains(title))
        if "logbook" in request.json:
            logbook = request.json["logbook"]
            entries = entries.where(Entry.logbook_id == logbook)
        if "authors" in request.json:
            authors = request.json["authors"]
            entries = entries.where(Entry.authors.contains(authors))
        page = int(request.json.get("page", 1))
        entries_per_page = int(request.json.get("n", 10))
        entries = entries.paginate(page, entries_per_page)
        return [model_to_dict(entry) for entry in entries]
