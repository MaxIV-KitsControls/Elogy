from flask import jsonify
from flask_restful import Resource, reqparse, marshal, marshal_with
from playhouse.shortcuts import dict_to_model

from ..db import Logbook
from . import fields


logbooks_parser = reqparse.RequestParser()
logbooks_parser.add_argument("parent_id", type=int)
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
    def get(self, logbook_id=None, revision_n=None):

        if logbook_id:
            logbook = Logbook.get(Logbook.id == logbook_id)
            if revision_n is not None:
                return logbook.get_revision(revision_n)
            return logbook

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

    @marshal_with(fields.logbook, envelope="logbook")
    def post(self, logbook_id=None):
        "Create a new logbook"
        args = logbooks_parser.parse_args()
        print(args, logbook_id)
        logbook = Logbook(name=args["name"], parent=args["parent_id"],
                          description=args["description"],
                          template=args["template"],
                          attributes=args["attributes"],
                          metadata=args["metadata"],
                          archived=args["archived"])
        if logbook_id is not None:
            parent = Logbook.get(Logbook.id == logbook_id)
            logbook.parent = parent
        logbook.save()
        return logbook

    @marshal_with(fields.logbook, envelope="logbook")
    def put(self, logbook_id):
        "Update an existing logbook"
        logbook = Logbook.get(Logbook.id == logbook_id)
        args = logbooks_parser.parse_args()
        logbook.make_change(**args).save()
        logbook.save()
        return logbook


class LogbookRevisionsResource(Resource):

    @marshal_with(fields.logbook_revisions)
    def get(self, logbook_id):
        logbook = Logbook.get(Logbook.id == logbook_id)
        return {"logbook_revisions": logbook.revisions}
