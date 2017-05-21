from datetime import datetime
import json

from flask import jsonify, url_for
from flask_restful import Resource, reqparse
from werkzeug import FileStorage

from ..attachments import save_attachment
from ..utils import get_utc_datetime


attachments_parser = reqparse.RequestParser()
attachments_parser.add_argument(
    "attachment", type=FileStorage, action="append",
    location='files', required=True)
attachments_parser.add_argument("timestamp", type=str)
attachments_parser.add_argument("metadata", type=str)
attachments_parser.add_argument("embedded", type=bool,
                                default=False)


class AttachmentsResource(Resource):

    def post(self, logbook_id, entry_id):
        "Upload attachments to an entry"
        args = attachments_parser.parse_args()
        if args["timestamp"]:
            timestamp = get_utc_datetime(args["timestamp"])
        else:
            timestamp = datetime.utcnow()
        if args.get("metadata"):
            metadata = json.loads(args["metadata"])
        else:
            metadata = None
        for attachment in args["attachment"]:
            print(attachment)
            attachment = save_attachment(attachment, timestamp,
                                         entry_id, metadata,
                                         embedded=args["embedded"])
            attachment.save()
        return jsonify(location=url_for("get_attachment",
                                        path=attachment.path),
                       content_type=attachment.content_type,
                       filename=attachment.filename,
                       metadata=attachment.metadata)
