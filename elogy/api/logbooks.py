from flask import jsonify
from flask_restful import Resource, reqparse, marshal, marshal_with
from playhouse.shortcuts import dict_to_model

from ..db import Logbook
from . import fields


logbooks_parser = reqparse.RequestParser()
logbooks_parser.add_argument("parent", type=int)
logbooks_parser.add_argument("name", type=str, required=True)
logbooks_parser.add_argument("description", type=str)
logbooks_parser.add_argument("template", type=str)
logbooks_parser.add_argument("attributes", type=list,
                             location="json", default=[])
logbooks_parser.add_argument("metadata", type=dict, location="json",
                             default={})
logbooks_parser.add_argument("archived", type=bool, default=False)


class LogbooksResource(Resource):

    "Handle requests for logbooks"

    @marshal_with(fields.logbook, envelope="logbook")
    def get(self, logbook_id=None):

        if logbook_id:
            return Logbook.get(Logbook.id == logbook_id)

        # Get either the direct children of a given parent, or else the
        # global list of top-level (no parent) logbooks
        parser = reqparse.RequestParser()
        parser.add_argument("parent", type=int)
        args = parser.parse_args()
        parent_id = args.get("parent")
        if parent_id:
            return Logbook.get(Logbook.id == parent_id)
        children = (Logbook.select()
                    .where(Logbook.parent == None))
        return dict(children=children)

    def post(self):
        "Create a new logbook"
        args = logbooks_parser.parse_args()
        logbook = dict_to_model(Logbook, args)
        logbook.save()
        return jsonify(logbook_id=logbook.id)

    def put(self, logbook_id):
        "Update an existing logbook"
        logbook = Logbook.get(Logbook.id == logbook_id)
        args = logbooks_parser.parse_args()
        change = logbook.make_change(args)
        logbook.save()
        change.save()
        return jsonify(revision_id=change.id)
