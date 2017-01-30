"""
This blueprint deals with attachments, e.g. arbitrary (well...) files that
are uploaded as part of an entry. They are stored as original files,
in a configurable location on disk.
"""

from datetime import datetime
import os

from flask import (Blueprint, abort, request,
                   current_app, jsonify, send_from_directory)
from PIL import Image

attachments = Blueprint('attachments', __name__,
                        template_folder='templates')


def allowed_file(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower()
            in current_app.config["ALLOWED_EXTENSIONS"])


@attachments.route("/", methods=["POST"])
def post_attachment():

    # entry_id = request.form["entry"]
    file_ = request.files["file"]
    print("attachment", request.form.get("entry"))

    if file_ and allowed_file(file_.filename):
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], file_.filename)

        if not os.path.exists(path):

            # The path is assumed to be contain today's date and the
            # file size, so it seems pretty safe to assume that if we
            # already have a file of the same name, we don't need to
            # rewrite it.

            directory = os.path.dirname(path)
            if not os.path.exists(directory):
                os.makedirs(directory)

            file_.save(path)

            # create a tiny preview version of the image
            image = Image.open(file_)
            image.thumbnail((100, 100))
            image.save(path + ".thumbnail", "JPEG")

        return jsonify({"location": "/" + path})
    else:
        abort(500)


@attachments.route("/<path:filename>")
def get_attachment(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
