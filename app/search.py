from flask import Blueprint, render_template, abort, request, redirect, url_for

from .db import Entry


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

    limit = int(parameters.get("limit", 100))

    results = Entry.select()
    if parameters.get("content"):
        regexp = ".*{content}.*".format(**parameters)
        results = results.where((Entry.content != None) &
                                Entry.content.regexp(regexp))
    if parameters.get("title"):
        results = results.where((Entry.title != None) &
                                Entry.title.regexp(parameters["title"]))
    if parameters.get("authors"):
        results = results.where(Entry.authors
                                .extract("")
                                .contains(parameters["authors"]))

    return render_template('search_results.jinja2', parameters=parameters,
                           entries=results.limit(limit))
