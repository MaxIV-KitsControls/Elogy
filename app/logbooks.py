from flask import (Blueprint, render_template, abort, request, redirect,
                   url_for, jsonify, current_app)
from jinja2 import TemplateNotFound
from peewee import fn, JOIN, DoesNotExist

from .db import Logbook
from .utils import request_wants_json
from . import actions


logbooks = Blueprint('logbooks', __name__)


@logbooks.route('/', methods=["GET"])
def get_logbooks():
    try:
        logbooks = (Logbook.select()
                    .where(Logbook.parent == 0))
        return render_template('logbooks.jinja2', children=logbooks)
    except DoesNotExist:
        abort(404)
    except TemplateNotFound:
        abort(404)


@logbooks.route('/<int:logbook_id>', methods=["GET", "POST"])
def show_logbook(logbook_id):
    if request.args:
        followups = request.args.get("followups", "").lower() == "true"
        attribute_filters = {}
        if "filters" in request.args:
            for attr_filter in request.args["filters"].split(","):
                attribute, value = attr_filter.split(":")
                attribute_filters[attribute] = value
    else:
        followups = request.form.get("followups", "").lower() == "on"
        attribute_filters = {}
        for name, value in request.form.items():
            if name.startswith("attribute-"):
                attribute = name.split("-", 1)[-1]
                if value != "[{}]".format(attribute):
                    attribute_filters[attribute] = value

    print("attribute_filters", attribute_filters)
    logbook = Logbook.get(Logbook.id == logbook_id)
    n_entries = int(request.args.get("n", 100))
    entries = logbook.get_entries(n=n_entries, followups=followups,
                                  attribute_filters=attribute_filters)

    return render_template(
        "logbook.jinja2", logbook=logbook, entries=entries,
        followups=followups, n_entries=n_entries,
        attribute_filters=attribute_filters)


@logbooks.route("/new")
def new_logbook():
    "Deliver a form for posting a new entry"
    data = request.args
    parent_id = int(data.get("parent", 0))
    if parent_id:
        parent = Logbook.get(Logbook.id == parent_id)
    else:
        parent = None
    return render_template('edit_logbook.jinja2',
                           parent=parent, logbook=None)


@logbooks.route("/<int:logbook_id>/edit")
def edit_logbook(logbook_id):
    "Deliver a form for posting a new entry"
    logbook = Logbook.get(Logbook.id == logbook_id)
    if logbook.parent:
        parent = Logbook.get(Logbook.id == logbook.parent)
    else:
        parent = None
    return render_template('edit_logbook.jinja2',
                           parent=parent, logbook=logbook)


@logbooks.route('/', methods=["POST"])
def write_logbook():
    "Handle form data creating or editing a logbook"
    if request.form:
        data = request.form

        attributes = []
        attr_keys = [(key, name)
                     for key, name in data.items()
                     if name and key.startswith("attribute-name-")]
        for key, name in sorted(attr_keys):
            n = key.rsplit("-", 1)[-1]
            attributes.append({
                "name": name,
                "type": data["attribute-type-{}".format(n)],
                "required": bool(data.get("attribute-required-{}".format(n))),
                "options": [
                    option.strip()
                    for option
                    in data.get("attribute-options-{}".format(n)).split("\n")
                ]
            })
    else:
        data = request.json
        attributes = data.get("attributes")

    parent_id = int(data.get("parent", 0))
    if parent_id:
        parent = Logbook.get(Logbook.id == parent_id)
        if not parent:
            abort(404)
    else:
        parent = None

    new = False
    if int(data.get("logbook", 0)):
        lb = Logbook.get(Logbook.id == data["logbook"])
        lb.name = data["name"]
        lb.description = data["description"]
        lb.attributes = attributes
        lb.parent = parent
    else:
        new = True
        lb = Logbook(name=data["name"],
                     description=data.get("description", ""),
                     attributes=attributes,
                     parent=parent)
    lb.save()

    # perform actions
    app = current_app._get_current_object()
    if new:
        actions.new_logbook.send(app, logbook=lb)
    else:
        actions.edit_logbook.send(app, logbook=lb)

    if request_wants_json():
        return jsonify(logbook_id=lb.id)
    return redirect("/#/logbook/{}".format(lb.id))
