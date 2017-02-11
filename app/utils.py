from flask import request


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
