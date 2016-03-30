#coding=utf8
import logging, urlparse
from django.http import HttpResponseBadRequest, HttpResponseServerError
from contentservice.utils.perf import perf_logged
from contentservice.utils import exception_handled
from contentservice.api import json_response, extract_parameters
from contentservice.models.novel import NovelModel, NovelRankModel
from contentservice.settings import STATIC_SERVER

_LOGGER = logging.getLogger("api_novel")

NOVEL_TXT_BASE = urlparse.urljoin("http://" + STATIC_SERVER, "/novel/txt/")

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def novel_listtype(request):
    ranks = NovelRankModel().find()
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
def novel_list(request):
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
    
    rank = NovelRankModel().find_one({'type' : list_type})
    if not rank:
        return HttpResponseBadRequest("Invalid type - %s" % list_type)
    items = get_novels(rank['novels'][index : index + limit])
    total = len(rank['novels'])
    
    return {"items" : [item.export() for item in items], "total" : total}


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def novel(request):
    spec = {
            "id" : "",
            "title" : "",
            }
    params = extract_parameters(request, spec)
    if params["id"]:
        query = {"_id" : params["id"]}        
    elif params["title"]:
        query = {"title" : params["title"]}
    else:
        return HttpResponseBadRequest("id or title is required")
    
    item = NovelModel().find_one(query)
    
    if not item:
        return
    return item.export()


def get_novels(titles):
    assert isinstance(titles, list)
    
    items = NovelModel().find({"title" : {"$in" : titles}}) if titles else []
    mapping = {}
    for item in items:
        mapping[item["title"]] = item
    
    novels = []
    for title in titles:
        novel = mapping.get(title)
        if novel:
            novels.append(novel)
    return novels
