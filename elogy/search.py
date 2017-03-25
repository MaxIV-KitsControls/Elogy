from flask import Blueprint, render_template, abort, request, redirect, url_for

from .db import Entry, Attachment
from peewee import JOIN


search = Blueprint('search', __name__)


@search.route("/")
def perform_search():
    parameters = request.args
    # for term in request.args.getlist("term"):
    #     if ":" in term:
    #         field, string = [s.strip() for s in term.split(":", 1)]
    #     else:
    #         field = "content"
    #         string = term
    #     parameters[field] = string

    print("parameters", parameters)

    logbook = int(parameters.get("logbook", 0))
    this_logbook = parameters.get("this-logbook") == "on"
    include_children = parameters.get("include-children") == "on"

    limit = int(parameters.get("limit", 100))

    terms = {}

    # start with all entries
    results = Entry.select()

    if this_logbook and logbook:
        if include_children:
            results = results.where(Entry.logbook == logbook)
            # TODO: figure out a good query here!
        else:
            results = results.where(Entry.logbook == logbook)
        terms["logbook"] = parameters["logbook"]

    # further filters on the results, depending on search criteria
    if parameters.get("content"):
        # let's do a stupid substring search for now
        substring = parameters["content"].replace("*", "%")
        results = results.where((Entry.content != None) &
                                Entry.content.contains(substring))
        terms["content"] = parameters["content"]
    if parameters.get("title"):
        results = results.where((Entry.title != None) &
                                Entry.title.regexp(parameters["title"]))
        terms["title"] = parameters["title"]
    if parameters.get("authors"):
        results = results.where(Entry.authors
                                .extract("")
                                .contains(parameters["authors"]))
        terms["authors"] = parameters["authors"]
    if parameters.get("attachments"):
        query = parameters["attachments"]
        results = (results
                   .join(Attachment)
                   .where(
                       (~ Attachment.embedded) &
                       # Here, ** means "case insensitive like" or ILIKE
                       (Attachment.path ** "%{}%".format(query)))
                   # avoid multiple hits on the same entry
                   .group_by(Entry.id))

    return render_template('search_results.jinja2', parameters=terms,
                           entries=results.limit(limit))
