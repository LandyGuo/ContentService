#coding=utf8
import logging
from django.http import HttpResponseBadRequest, HttpResponseServerError
from contentservice.utils.perf import perf_logged
from contentservice.utils import exception_handled
from contentservice.api import json_response, extract_parameters
from contentservice.models.video import VideoAlbumModel, VideoRankModel,VideoTopModel

_LOGGER = logging.getLogger("api_video")

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def album_list(request):
    spec = {
            "index" : 0,
            "limit" : 20,
            "aid":None,
           }
    params = extract_parameters(request, spec)
    albums = []
    aid = params.get('aid', None)
    if aid:
        albums = VideoAlbumModel().find({'id': aid}, sort = [('time', -1)])
    else:
        index = params['index']
        limit = params['limit']
        if index < 0:
            index = 0
        if limit <= 0 or limit >= 100:
            limit = 20

        albums = VideoAlbumModel().find({}, skip = index, limit = limit, sort = [('time', -1)])
    total = VideoAlbumModel().collection().count()

    return {"items" : [item.export() for item in albums], "total" : total}


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def rank_type(request):
    ranks = VideoRankModel().find()
    items = []
    for rank in ranks:
        item = {
                "title" : rank["title"],
                "type" : rank["type"],
                }
        items.append(item)
    return {"items" : items, "total" : len(items)}

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def rank(request):
    spec = {
              "type" : "",
              "index" : 0,
              "limit" : 20,
            }
    params = extract_parameters(request, spec)
    list_type = params['type']
    index = params['index']
    limit = params['limit']
    if not list_type:
        return HttpResponseBadRequest("Missing type")
    if index < 0:
        index = 0
    if limit <= 0 or limit >= 100:
        limit = 20

    rank = VideoRankModel().find_one({'type' : list_type})
    if not rank:
        return HttpResponseBadRequest("Invalid type - %s" % list_type)
    items = get_albums(rank['videos'][index : index + limit])
    total = len(rank['videos'])

    return {"items" : [item.export() for item in items], "total" : total}

@json_response
def VideoRankResponse(request):
    LIST_CONTENT = ['type','source','priority','channel','updatetime','list']
    response = []
    params = {}
    GET = request.GET
    for s in ('channel','source'):
        if GET.get(s):
            params[s] = GET.get(s)
    items = VideoTopModel().collection().find(params)
    for item in items:
        episode = {}
        for content in LIST_CONTENT:
            episode[content] = item.get(content)
        response.append(episode)
    return response

def get_albums(ids):
    items = VideoAlbumModel().find({"_id" : {"$in" : ids}}) if ids else []
    mapping = {}
    for item in items:
        mapping[item["_id"]] = item

    albums = []
    for _id in ids:
        album = mapping.get(_id)
        if album:
            albums.append(album)
    return albums
