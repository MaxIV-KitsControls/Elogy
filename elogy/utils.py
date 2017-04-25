from datetime import datetime

from flask import request
from flask.json import JSONEncoder
import peewee
from playhouse.shortcuts import model_to_dict


def request_wants_json():
    "Check whether we should send a JSON reply"
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    print(best)
    print(request.accept_mimetypes[best],
          request.accept_mimetypes['text/html'])

    return best == 'application/json' and \
        request.accept_mimetypes[best] >= \
        request.accept_mimetypes['text/html']


class CustomJSONEncoder(JSONEncoder):

    """JSON serializer for objects not serializable by default json code"""

    def default(self, obj):
        if isinstance(obj, datetime):
            serial = obj.timestamp()
            return serial
        elif isinstance(obj, peewee.SelectQuery):
            print("select")
            return list(obj)
        elif isinstance(obj, peewee.Model):
            serial = model_to_dict(obj, recurse=False)
            return serial

        return JSONEncoder.default(self, obj)
