"""
This blueprint deals with attachments, e.g. arbitrary (well...) files that
are uploaded as part of an entry. They are stored as original files,
in a configurable location on disk.
"""

from datetime import datetime
from dateutil.parser import parse
import os

from flask import (Blueprint, abort, request, url_for,
                   current_app, jsonify, send_from_directory)
from PIL import Image

from . import db

attachments = Blueprint('attachments', __name__,
                        template_folder='templates')


def allowed_file(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower()
            in current_app.config["ALLOWED_EXTENSIONS"])


def save_attachment(file_, timestamp, entry_id, embedded=False):
    # make up a path and unique filename using the timestamp
    # TODO: make this smarter, somehow
    today = timestamp.strftime("%Y/%m/%d")
    epoch = timestamp.strftime("%s")
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], today)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    filename = "{}-{}".format(epoch, file_.filename)
    # url = url_for(".get_attachment", "{}/{}".format(today, filename))
    path = os.path.join(upload_dir, filename)
    file_.save(path)
    try:
        # If it's an image file we create a thumbnail version for preview
        image = Image.open(file_)
        width, height = image.size
        metadata = dict(size={"width": width, "height": height})
        if width > 100 or height > 100:
            # create a tiny preview version of the image
            image.convert("RGB")
            image.thumbnail((100, 100))
            try:
                image.save(path + ".thumbnail", "JPEG")
                width, height = image.size
                metadata["thumbnail_size"] = {"width": width, "height": height}
            except IOError as e:
                print("Error making thumbnail", e)
        else:
            os.link(path, path + ".thumbnail")
    except IOError:
        # Not a recognized image
        metadata = None

    if entry_id:
        entry = db.Entry.get(db.Entry.id == entry_id)
    else:
        entry = None
    attachment = db.Attachment.create(path="{}/{}".format(today, filename),
                                      timestamp=timestamp,
                                      content_type=file_.content_type,
                                      entry=entry, embedded=embedded,
                                      metadata=metadata)
    return attachment


@attachments.route("/", methods=["POST"])
@attachments.route("/<int:entry_id>", methods=["POST"])
def post_attachment(entry_id=None):
    file_ = request.files["file"]
    timestamp = request.form.get("timestamp")
    embedded = request.form.get("embedded", "false").lower() == "true"

    if timestamp:
        timestamp = parse(timestamp)
    else:
        timestamp = datetime.now()
    if file_:  # and allowed_file(file_.filename):
        attachment = save_attachment(file_, timestamp, entry_id,
                                     embedded=embedded)
        return jsonify({"location": url_for(".get_attachment",
                                            filename=attachment.path)})
    else:
        abort(500)


@attachments.route("/<path:filename>")
def get_attachment(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
