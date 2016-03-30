# -*- coding: utf-8 -*-
import logging, json, base64
from hashlib import md5
from time import time
from datetime import datetime
from django.http import HttpResponse, HttpResponseForbidden,\
                    HttpResponseBadRequest, HttpResponseServerError
from contentservice.utils import datetimeutil, typeutil
from contentservice.utils import cryptoutil, exception_handled
from contentservice.utils.perf import perf_logged
from contentservice.models import MODEL_TYPES, create_model

_LOGGER = logging.getLogger("api")

_TIMESTAMP_DELTA = 180

def json_handler(obj):
    if isinstance(obj, datetime):
        return datetimeutil.unix_time(obj)
    else:
        _LOGGER.error(obj)
        raise TypeError

def json_response(func):
    def decorator(request):
        data = func(request)
        if isinstance(data, HttpResponse):
            return data
        resp = HttpResponse(json.dumps(data, default = json_handler))
        resp["Content-Type"] = "application/json; charset=utf-8"
        return resp
    return decorator

def encrypt_required(func):
    def decorator(request, *args, **kwargs):
        try:
            data = cryptoutil.private_decrypt(base64.b64decode(request.body))
        except:
            data = None
        if not data:
            return HttpResponseForbidden()
        request.body = data

        resp = func(request, *args, **kwargs)

        if resp.content:
            resp.content = base64.b64encode(cryptoutil.private_encrypt(resp.content))

        return resp

    return decorator

def signature_required(func):

    def verify_timestamp(timestamp):
        if (not timestamp) or (not timestamp.isdigit()):
            return False
        timestamp = int(timestamp)
        timestamp_now = int(time())
        if abs(timestamp - timestamp_now) > _TIMESTAMP_DELTA:
            return False
        return True

    def calc_signature(data, timestamp):
        salt = "dolphin"
        sig = md5(md5(data + salt).hexdigest() + timestamp + salt).hexdigest()
        return sig

    def decorator(request, *args, **kwargs):
        timestamp = request.COOKIES.get("timestamp")
        sig = request.COOKIES.get("signature")

        if not verify_timestamp(timestamp):
            _LOGGER.info("Invalid timestamp = %s" % timestamp)
            return HttpResponseForbidden("Invalid timestamp")

        if (not sig) or (sig != calc_signature(request.body, timestamp)):
            _LOGGER.info("Invalid signature - %s (body = %s, timestamp = %s)" % (sig, request.body, timestamp))
            return HttpResponseForbidden("Invalid signature")

        return func(request, *args, **kwargs)

    return decorator

def extract_parameters(request, spec):
    params = {}
    for key, default in spec.iteritems():
        if isinstance(default, list):
            value = request.REQUEST.getlist(key, default)
        else:
            value = request.REQUEST.get(key, default)

        if isinstance(default, int):
            try:
                value = int(value)
            except:
                value = default
        elif isinstance(default, float):
            try:
                value = float(value)
            except:
                value = default

        params[key] = value

    return params


@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def server_info(request):
    '''
    Must be first call for every client.
    Returns client update info, server time (for signature), etc.

    Request:
    No parameter, no authentication needed

    Response:
    {
        "server_time" : 1361969522,
        "client_info" : {},
    }
    '''

    data = {
            "server_time" : datetime.utcnow(),
            }

    return data


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def contents(request):
    '''
    Get content list

    Parameters:
    {
        "type" : "video",
        "index" : 0,
        "limit" : 20,
        "updated" : unix_time,
        "id" : "xxxx",
        "source" : "",
    }

    Response:
    {
        "items" :
            [{
            }],
    }
    '''

    spec = {
            "type" : u"",
            "index" : 0,
            "limit" : 20,
            "updated" : 0,
            "source" : u"",
            "album_id":u"",
            }
    params = extract_parameters(request, spec)

    type = request.GET.get("type")
    if (params["type"] not in MODEL_TYPES.keys()):
        return HttpResponseBadRequest("Invalid type - %s" % type)

    updated = params["updated"]
    if not updated:
        updated = datetime.utcfromtimestamp(0)
    else:
        updated = datetime.utcfromtimestamp(int(updated))

    model = create_model(type)
    items = []
    album_id = params["album_id"]
    if album_id:
        if params["type"] == "video.album":
            query = {"_id": album_id}
        elif params["type"] == "video.chapter":
            query = {"album_id": album_id}
        else:
            return HttpResponseBadRequest("Invalid type with album_id - %s, %s" % (type,album_id))
        items = model.find(query)
    else:
        source = params["source"]

        limit = params["limit"]
        index = params["index"]
        if index < 0:
            index = 0
        if limit <= 0 or limit > 1000:
            limit = 20

        query = {"updated" : {"$gte" : updated}}
        if source:
            query['source'] = source

        items = model.find(query, sort = [("updated", 1)], skip = index, limit = limit)
    ret = {"items" : [item.export() for item in items]}
    return ret
