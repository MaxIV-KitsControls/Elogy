"""Utilities for dealing with attachments, e.g. arbitrary (well...)
files that are uploaded as part of an entry. They are stored as
original files, in a configurable location on disk.
"""

from base64 import decodestring
import binascii
from datetime import datetime
from dateutil.parser import parse
import io
import mimetypes
import os

from flask import (Blueprint, abort, request, url_for, redirect,
                   current_app, jsonify, send_from_directory)
from lxml import html, etree
from lxml.html.clean import Cleaner
from PIL import Image
from werkzeug import FileStorage

from .db import Entry, Attachment


def allowed_file(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower()
            in current_app.config["ALLOWED_EXTENSIONS"])


def get_content_type(file_):
    "Try to figure out the mimetype of the fiven file"
    if file_.content_type is not None:
        return file_.content_type
    type_, encoding = mimetypes.guess_type(file_.filename)
    if type_ is None:
        return None
    if encoding is not None:
        return "{};{}".format(type_, encoding)
    return type_


def save_attachment(file_, timestamp, entry_id, metadata=None, embedded=False):
    "Store an attachment in the proper place"
    # make up a path and unique filename using the timestamp
    # TODO: make this smarter, somehow
    today = timestamp.strftime("%Y/%m/%d")
    epoch = timestamp.strftime("%s")
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], today)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    # make sure there's no path part in the filename
    sanitized_filename = os.path.basename(file_.filename)
    prefixed_filename = "{}-{}".format(epoch, sanitized_filename)
    path = os.path.join(upload_dir, prefixed_filename)
    # store the attachment at the unique path
    file_.save(path)
    try:
        # If it's an image file we create a thumbnail version for preview
        image = Image.open(file_)
        width, height = image.size
        new_metadata = dict(size={"width": width, "height": height})
        if metadata:
            new_metadata.update(**metadata)
        if width > 100 or height > 100:
            # create a tiny version of the image
            image.convert("RGB")
            image.thumbnail((100, 100))
            if ((image.mode in ("RGBA", "LA")) or
                (image.mode == 'P' and "transparency" in image.info)):
                # image has transparency. Since JPEG does not support alpha
                # channel, we'll superimpose it on a white background.
                alpha = image.convert("RGBA").split()[-1]
                bg = Image.new("RGB", image.size, (255, 255, 255, 255))
                bg.paste(image, mask=alpha)
                image = bg
            try:
                image.save(path + ".thumbnail", "JPEG")
                width, height = image.size
                new_metadata["thumbnail_size"] = {"width": width,
                                                  "height": height}
            except IOError as e:
                print("Error making thumbnail", e)
        else:
            # small image, re-use it as its own thumbnail
            os.link(path, path + ".thumbnail")
    except IOError as e:
        # Not a recognized image, no thumbnail
        # TODO: thumbnails of PDF:s and maybe some other formats might be nice
        new_metadata = metadata

    if entry_id:
        entry = Entry.get(Entry.id == entry_id)
    else:
        entry = None

    content_type = get_content_type(file_)

    attachment = Attachment(path="{}/{}".format(today, prefixed_filename),
                            filename=sanitized_filename,
                            timestamp=timestamp,
                            content_type=content_type,
                            entry=entry, embedded=embedded,
                            metadata=new_metadata)
    return attachment


html_clean = Cleaner(style=True, inline_style=False,
                     safe_attrs=html.defs.safe_attrs | set(['style']))


def decode_base64(data):
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    missing_padding = len(data) % 4
    if missing_padding != 0:
        data += b'=' * (4 - missing_padding)
    return decodestring(data)


def handle_img_tags(text, entry_id=None, timestamp=None):
    """Get image tags from the text. Extract embedded images and save
    them as attachments"""
    attachments = []
    timestamp = timestamp or datetime.now()
    try:
        doc = html.document_fromstring(text)
    except etree.ParserError:
        return text, attachments

    for i, element in enumerate(doc.xpath("//*[@src]")):
        src = element.attrib['src'].split("?", 1)[0]
        if src.startswith("data:"):
            header, data = src[5:].split(",", 1)  # TODO: find a safer way
            filetype, encoding = header.split(";")
            try:
                raw_image = decode_base64(data.encode("ascii"))
            except binascii.Error as e:
                print("failed to decode image!", e)
                continue
            try:
                # TODO: possible to be more clever about the filename?
                filename = "inline-{}-{}.{}".format(
                    len(raw_image), i, filetype.split("/")[1].lower())
            except IndexError:
                print("weird filetype!?", filetype)
                continue
            file_ = FileStorage(io.BytesIO(raw_image),
                                filename=filename, content_type=filetype)
            attachment = save_attachment(file_, timestamp, entry_id,
                                         embedded=True)
            # TODO: maybe it would be a better idea to use a URL like
            # "/attachments/<id>" here, and then just have a redirect
            # to the real URI? That way we could change the way the files
            # are stored under the hood without bothering about having
            # to keep URLs unchanged...
            src = element.attrib["src"] = url_for("get_attachment",
                                                  path=attachment.path)
            if element.getparent().tag == "a":
                element.getparent().attrib["href"] = src
            else:
                parent = element.getparent()

                wrapper = etree.Element('a')
                wrapper.attrib['href'] = src

                loc = parent.index(element)
                parent.insert(loc, wrapper)

                parent.remove(element)
                wrapper.append(element)

            attachments.append(attachment)

    # throw in a cleanup here since we've already parsed the HTML
    html_clean(doc)  # remove some evil tags
    content = '\n'.join(
        (etree
         .tostring(stree, pretty_print=True, method="xml")
         .decode("utf-8")
         .strip())
        for stree in doc[0].iterchildren()
    )

    return content, attachments


