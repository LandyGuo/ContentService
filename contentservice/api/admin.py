import re
import logging
import json
from datetime import datetime
from django.http import HttpResponseServerError
from django.views.decorators.http import require_GET, require_POST
from contentservice.models.video import VideoSourceModel, VideoAlbumModel
from contentservice.crawler import Scheduler
from contentservice.utils.perf import perf_logged
from contentservice.utils import exception_handled
from contentservice.api import json_response

_LOGGER = logging.getLogger("api_admin")

def _query_video(model, page, count, query, field_exclude=['related','authorities'], sort=[('created',-1)]):
    fields = {}
    if field_exclude:
        fields.update(dict([ (k, 0) for k in field_exclude ]))
    cond = {'deleted':False}
    if query:
        cond.update({'title':{'$regex': re.compile(ur'.*%s.*' % query, re.I)}})
    albums = model().find(query=cond, fields=fields, skip=((page-1)*count), limit=count, sort=sort)
    albums = [ a.export() for a in albums ]
    return  albums

@require_GET
@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def query_video_albums(request):
    page =  int(request.GET.get('p', 1))
    count =  int(request.GET.get('c', 20))
    query =  request.GET.get('q', '')
    return _query_video(VideoAlbumModel, page, count, query,sort=[('pubtime',-1)])


@require_GET
@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def query_video_sources(request):
    page =  int(request.GET.get('p', 1))
    count =  int(request.GET.get('c', 20))
    query =  request.GET.get('q', '')
    return _query_video(VideoSourceModel, page, count, query)

@require_POST
@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def remerge_video(request):
    source_id =  request.GET.get('sid', None)
    album_id =  request.GET.get('aid', None)
    vs = VideoSourceModel().find_one(query={'_id':source_id})
    va = VideoAlbumModel().find_one(query={'_id':album_id})
    if vs and va:
        vs.on_import(to_album_id=album_id)
        return {'status':1}
    else:
        return {'status':-1}


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def crawler_job(request):
    if request.method == "GET":
        url =  request.GET.get('url', None)
        raw_job = Scheduler.get_job_from_url(url)
        job = {}
        if raw_job:
            job = {
                    'type': raw_job['type'],
                    'key':  raw_job['key'],
                    'priority': raw_job['priority'],
                    'interval': raw_job['interval'],
                    'lastrun': raw_job['lastrun'],
                    'status': raw_job['status'],
                    'to_album_id': raw_job['data'].get('to_album_id'),
                    }
        return job
    else:
        url =  request.GET.get('url', None)
        interval =  request.GET.get('interval', 3600)
        channel =  request.GET.get('channel', None)
        image =  request.GET.get('image', None)
        data = {
                'channel':channel,
                'image': image,
                }
        success = Scheduler.schedule_url(url, data=data, interval=int(interval), reset=True)
        return {'status': int(success)}

from pymongo import MongoClient
from django.conf import settings
_conn = MongoClient(settings.MONGO_CONN_STR)
_crawler_db = _conn["crawler"]

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def crawler_conf(request):
    if request.method == "GET":
        page =  int(request.GET.get('p', 1))
        count =  int(request.GET.get('c', 20))
        data = [ x for x in  _crawler_db.crawler_conf.find(skip=((page-1)*count), limit=count, fields={'_id':0})]
        return data
    else:
        data = json.loads(request.body)
        if 'type' not in data:
            return {'status':-1}
        else:
            data['updated'] = datetime.utcnow()
            _crawler_db.crawler_conf.update({'type':data['type']},{'$set':data}, upsert=True)
            return {'status':1}




@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def crawler_process(request):
    if request.method == "GET":
        page =  int(request.GET.get('p', 1))
        count =  int(request.GET.get('c', 20))
        data = [ x for x in  _crawler_db.crawler_process.find(skip=((page-1)*count), limit=count, fields={'_id':0})]
        return data
    else:
        data = json.loads(request.body)
        if 'category' not in data:
            return {'status':-1}
        else:
            data['updated'] = datetime.utcnow()
            _crawler_db.crawler_process.update({'category':data['category']},{'$set':data}, upsert=True)
            return {'status':1}

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def crawler_command(request):
    command = request.GET.get('cmd', None)
    if command:
        data = {
                'command': command,
                'created': datetime.utcnow(),
                'status' : 0,
                }
        _crawler_db.crawler_command.save(data)

@json_response
def schedule(request):
    response = {}
    type = request.GET.get("type")
    nextrun = request.GET.get("nextrun")
    if type.endswith("album"):
        response['error_info'] = "Type Error."
        response['status'] = False
        return response
    try:
        nextrun = datetime.strptime(nextrun, "%Y-%m-%d-%H-%M-%S")
    except:
        response['error_info'] = "Datetime Error."
        response['status'] = False
        return response
    
    m = Scheduler.monitor_schedule(type, nextrun)
    if m is not None:
        response['error_info'] = ""
        response['status'] = True
    else:
        response['error_info'] = "Type Error."
        response['status'] = False
    return response
