from flask import Blueprint, render_template, abort, request, redirect, url_for
from jinja2 import TemplateNotFound
from peewee import fn, JOIN, DoesNotExist

from .db import Logbook


logbooks = Blueprint('logbooks', __name__)


@logbooks.route('/', methods=["GET"])
def get_logbooks():
    try:
        logbooks = (Logbook.select()
                    .where(Logbook.parent == 0))
        return render_template('logbooks.html', children=logbooks)
    except DoesNotExist:
        abort(404)
    except TemplateNotFound:
        abort(404)


@logbooks.route('/<int:logbook_id>', methods=["GET"])
def show_logbook(logbook_id):
    logbook = Logbook.get(Logbook.id == logbook_id)
    page = int(request.args.get("page", 0))
    entries_per_page = int(request.args.get("entries_per_page", 0))
    return render_template(
        "logbook.html", logbook=logbook,
        page=page, entries_per_page=entries_per_page)


@logbooks.route("/new")
def new_logbook():
    "Deliver a form for posting a new entry"
    data = request.args
    parent_id = int(data.get("parent", 0))
    if parent_id:
        parent = Logbook.get(Logbook.id == parent_id)
    else:
        parent = None
    return render_template('edit_logbook.html',
                           parent=parent, logbook=None)


@logbooks.route("/<int:logbook_id>/edit")
def edit_logbook(logbook_id):
    "Deliver a form for posting a new entry"
    logbook = Logbook.get(Logbook.id == logbook_id)
    if logbook.parent:
        parent = Logbook.get(Logbook.id == logbook.parent)
    else:
        parent = None
    return render_template('edit_logbook.html',
                           parent=parent, logbook=logbook)


@logbooks.route('/', methods=["POST"])
def write_logbook():
    "Handle form data creating or editing a logbook"
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
                in data.get("attribute-options-{}".format(n)).split()
            ]
        })
    parent_id = int(data.get("parent", 0))
    if parent_id:
        parent = Logbook.get(Logbook.id == parent_id)
        if not parent:
            abort(404)
    else:
        parent = None
    if int(data.get("logbook", 0)):
        lb = Logbook.get(Logbook.id == data["logbook"])
        lb.name = data["name"]
        lb.description = data["description"]
        lb.attributes = attributes
        lb.parent = parent
    else:
        lb = Logbook(name=data["name"],
                     description=data.get("description", ""),
                     attributes=attributes,
                     parent=parent)
    lb.save()
    return redirect("/#/logbook/{}".format(lb.id))
