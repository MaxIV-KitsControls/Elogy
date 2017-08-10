from flask_restful import Resource, marshal_with
from webargs.fields import Integer, Str, Boolean, Dict, List, Nested
from webargs.flaskparser import use_args

from ..db import Logbook
from ..actions import new_logbook, edit_logbook
from . import fields, send_signal


logbook_args = {
    "parent_id": Integer(missing=0),
    "name": Str(),
    "description": Str(allow_none=True),
    "template": Str(allow_none=True),
    "attributes": List(Nested({
        "name": Str(),
        "type": Str(
            validate=lambda t: t in ["text",
                                     "number",
                                     "boolean",
                                     "option",
                                     "multioption"]),
        "required": Boolean(),
        "options": List(Str())
    })),
    "metadata": Dict(),
    "archived": Boolean(missing=False)
}


class LogbooksResource(Resource):

    "Handle requests for logbooks"

    @use_args({"parent": Integer()})
    @marshal_with(fields.logbook, envelope="logbook")
    def get(self, args, logbook_id=None, revision_n=None):

        "Fetch a given logbook"

        if logbook_id:
            logbook = Logbook.get(Logbook.id == logbook_id)
            if revision_n is not None:
                return logbook.get_revision(revision_n)
            return logbook

        # Get either the direct children of a given parent, or else the
        # global list of top-level (no parent) logbooks
        parent_id = args.get("parent")
        if parent_id:
            return Logbook.get(Logbook.id == parent_id)
        children = (Logbook.select()
                    .where(Logbook.parent == None))
        return dict(children=children)

    @send_signal(new_logbook)
    @use_args(logbook_args)
    @marshal_with(fields.logbook, envelope="logbook")
    def post(self, args, logbook_id=None):

        "Create a new logbook"

        logbook = Logbook(name=args["name"],
                          parent=args.get("parent_id"),
                          description=args.get("description"),
                          template=args.get("template"),
                          attributes=args["attributes"],
                          metadata=args.get("metadata", {}),
                          archived=args["archived"])
        if logbook_id:
            parent = Logbook.get(Logbook.id == logbook_id)
            logbook.parent = parent
        logbook.save()
        return logbook

    @send_signal(edit_logbook)
    @use_args(logbook_args)
    @marshal_with(fields.logbook, envelope="logbook")
    def put(self, args, logbook_id):

        "Update an existing logbook"

        logbook = Logbook.get(Logbook.id == logbook_id)
        logbook.make_change(**args).save()
        logbook.save()
        return logbook


class LogbookChangesResource(Resource):

    @marshal_with(fields.logbook_changes)
    def get(self, logbook_id):
        logbook = Logbook.get(Logbook.id == logbook_id)
        return {"logbook_changes": logbook.changes}
