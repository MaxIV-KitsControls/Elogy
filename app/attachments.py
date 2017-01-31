"""
This blueprint deals with attachments, e.g. arbitrary (well...) files that
are uploaded as part of an entry. They are stored as original files,
in a configurable location on disk.
"""

from datetime import datetime
import os

from flask import (Blueprint, abort, request, url_for,
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

    file_ = request.files["file"]

    if file_ and allowed_file(file_.filename):
        # make up a path and unique filename using the timestamp
        # TODO: make this smarter, somehow
        now = datetime.now()
        today = now.strftime("%Y/%m/%d")
        epoch = now.strftime("%s")
        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], today)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        filename = "{}-{}".format(epoch, file_.filename)
        url = os.path.join(url_for(".post_attachment"), today, filename)
        path = os.path.join(upload_dir, filename)
        file_.save(path)

        image = Image.open(file_)
        width, height = image.size
        if width > 100 or height > 100:
            # create a tiny preview version of the image
            image.thumbnail((100, 100))
            image.save(path + ".thumbnail", "JPEG")
        else:
            os.link(path, path + ".thumbnail")

        return jsonify({"location": url})
    else:
        abort(500)


@attachments.route("/<path:filename>")
def get_attachment(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
