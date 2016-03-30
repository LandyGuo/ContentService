#coding=utf8
import logging, random, os
from datetime import datetime
from django.http import HttpResponseBadRequest, HttpResponseServerError
from contentservice.utils.perf import perf_logged
from contentservice.utils import exception_handled
from contentservice.api import json_response, extract_parameters, signature_required
from contentservice.models.ring import RingToneModel, RingToneRankModel, RingBackModel, RingBackRankModel,\
                                RingSceneModel, RingSceneRankModel, RingUserModel, RingFeedbackModel
from contentservice.settings import STATIC_SERVER

_LOGGER = logging.getLogger("api_ring")

_CARRIERS = ["cm", "cu", "ct"]

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def scene_ranklist(request):
    spec = {
            'carrier' : ''
            }
    params = extract_parameters(request, spec)
    if params['carrier'] not in _CARRIERS:
        return HttpResponseBadRequest("Invalid carrier")
    
    fields = ['title', 'type', 'image']
    ranks = RingSceneRankModel().find(query = {"carrier" : params['carrier']}, fields = fields)
    items = [filter_dct(rank, fields) for rank in ranks]
    return {"total" : len(items), "items" : items}

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def ringback_ranklist(request):
    spec = {
            "carrier" : ""
            }
    params = extract_parameters(request, spec)
    if params["carrier"] not in _CARRIERS:
        return HttpResponseBadRequest("Invalid carrier")
    
    items = get_ringback_ranklist(params['carrier'])
       
    return {"total" : len(items), "items" : items}

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def ringtone_ranklist(request):
    items = get_ringtone_ranklist()
    return {"total" : len(items), "items" : items}

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def ring_ranklist(request):
    spec = {
            "carrier" : ""
            }
    params = extract_parameters(request, spec)
    if params["carrier"] not in _CARRIERS:
        return HttpResponseBadRequest("Invalid carrier")
    
    items = [
             {'ringtype' : 'ringtone', 'type' : 'hot', 'title' : u'热销', 'image' : ''},
             {'ringtype' : 'ringtone', 'type' : 'new', 'title' : u'飙升', 'image' : ''},
             {'ringtype' : 'ringtone', 'type' : 'webhot', 'title' : u'网络红歌', 'image' : ''},
             {'ringtype' : 'ringback', 'type' : 'joke', 'title' : u'搞笑彩铃', 'image' : ''},
             ]
    
#    ringtone_ranks = get_ringtone_ranklist()
#    for rank in ringtone_ranks:
#        rank['ringtype'] = 'ringtone'
#            
#    ringback_ranks = get_ringback_ranklist(params['carrier'])
#    for rank in ringback_ranks:
#        rank['ringtype'] = 'ringback'
#    
#    items = ringtone_ranks + ringback_ranks
    return {"total" : len(items), "items" : items}


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def scene_rank(request):
    spec = {
            'carrier' : '',
            'type' : '',
            'index' : 0,
            'limit' : 20,
            }
    params = extract_parameters(request, spec)
    if params['carrier'] not in _CARRIERS:
        return HttpResponseBadRequest("Invalid carrier")
    if not params['type']:
        return HttpResponseBadRequest("Missing type")
    if params["index"] < 0:
        params["index"] = 0
    if params["limit"] < 0 or params["limit"] > 100:
        params["limit"] = 20
    
    query = {'carrier' : params['carrier'], 'type' : params['type']}
    rank = RingSceneRankModel().find_one(query)
    if not rank:
        return HttpResponseBadRequest("Rank not found")
    
    ids = rank['scenes'][params['index'] : params['index'] + params['limit']]
    items = get_scenes(params['carrier'], ids)
            
    return {'total' : len(rank['scenes']), 'items' : scenes_export(items, params['carrier'])}

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def ringback_rank(request):
    spec = {
            'carrier' : '',
            'type' : '',
            'index' : 0,
            'limit' : 20,
            }
    params = extract_parameters(request, spec)
    if params["carrier"] not in _CARRIERS:
        return HttpResponseBadRequest("Invalid carrier")    
    if not params['type']:
        return HttpResponseBadRequest("Missing type")
    if params["index"] < 0:
        params["index"] = 0
    if params["limit"] < 0 or params["limit"] > 100:
        params["limit"] = 20
    
    rank = RingBackRankModel().find_one({'carrier' : params['carrier'], 'type' : params['type']})
    if not rank:
        return HttpResponseBadRequest("Rank not found")
    
    ids = rank['ringbacks'][params['index'] : params['index'] + params['limit']]
    ringbacks = get_ringbacks(params['carrier'], ids)
    
    return {'total' : len(rank['ringbacks']), 'items' : [item.export() for item in ringbacks]}

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def ringtone_rank(request):
    spec = {
            'type' : '',
            'index' : 0,
            'limit' : 20,
            }
    params = extract_parameters(request, spec)
    if not params['type']:
        return HttpResponseBadRequest("Missing type")
    if params["index"] < 0:
        params["index"] = 0
    if params["limit"] < 0 or params["limit"] > 100:
        params["limit"] = 20
    
    rank = RingToneRankModel().find_one({'type' : params['type']})
    if not rank:
        return HttpResponseBadRequest("Rank not found")
    
    ids = rank['ringtones'][params['index'] : params['index'] + params['limit']]
    ringtones = get_ringtones(ids)
    
    return {'total' : len(rank['ringtones']), 'items' : [item.export() for item in ringtones]}


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def scene_search(request):
    spec = {
            'carrier' : '',
            'query' : '',
            'index' : 0,
            'limit' : 20,
            'sort' : '',
            }
    params = extract_parameters(request, spec)
    if params['carrier'] not in _CARRIERS:
        return HttpResponseBadRequest("Invalid carrier")    
    if params["index"] < 0:
        params["index"] = 0
    if params["limit"] < 0 or params["limit"] > 100:
        params["limit"] = 20
    
    if not params['sort']:
        sort_key, sort_dir = "visits", -1
    else:
        sort_key, sort_dir = parse_sort(params['sort'])
  
    if params['query']:
        items = RingSceneModel().text_search(params["query"], filter = {"carrier" : params["carrier"]})
        if sort_key:
            items = sorted(items, key = lambda item:item[sort_key], reverse = (sort_dir == -1))
            
        total = len(items)
        items = items[params['index'] : params['index'] + params['limit']]
    else:
        items = RingSceneModel().find({"carrier" : params["carrier"]}, skip = params['index'], limit = params['limit'], sort = [(sort_key, sort_dir)] if sort_key else None)
        total = RingSceneModel().collection().find({"carrier" : params["carrier"]}).count()
    
    return {'total' : total, 'items' : scenes_export(items, params['carrier'])}

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def ringback_search(request):
    spec = {
            'carrier' : '',
            'query' : '',
            'sort' : '',
            'index' : 0,
            'limit' : 20,
            }
    params = extract_parameters(request, spec)
    if params['carrier'] not in _CARRIERS:
        return HttpResponseBadRequest("Invalid carrier")
    if params["index"] < 0:
        params["index"] = 0
    if params["limit"] < 0 or params["limit"] > 100:
        params["limit"] = 20
    
    sort_key, sort_dir = parse_sort(params['sort'])
    
    if params['query']:
        items = RingBackModel().text_search(params["query"], filter = {"source" : params["carrier"]})
        if sort_key:
            items = sorted(items, key = lambda item:item[sort_key], reverse = (sort_dir == -1))        
        total = len(items)
        items = items[params['index'] : params['index'] + params['limit']]
    else:
        items = RingBackModel().find({"source" : params["carrier"]}, skip = params['index'], limit = params['limit'], sort = [(sort_key, sort_dir)] if sort_key else None)
        total = RingBackModel().collection().find({"source" : params["carrier"]}).count() 
        
    return {'total' : total, 'items' : [item.export() for item in items]}     

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def ringtone_search(request):
    spec = {
            'query' : '',
            'index' : 0,
            'limit' : 20,
            'sort' : '',
            }
    params = extract_parameters(request, spec)
    if params["index"] < 0:
        params["index"] = 0
    if params["limit"] < 0 or params["limit"] > 100:
        params["limit"] = 20
    
    sort_key, sort_dir = parse_sort(params['sort'])
    if params['query']:
        items = RingToneModel().text_search(params["query"])
        if sort_key:
            items = sorted(items, key = lambda item:item[sort_key], reverse = (sort_dir == -1))
        total = len(items)
        items = items[params['index'] : params['index'] + params['limit']]
    else:
        items = RingToneModel().find({}, skip = params['index'], limit = params['limit'], sort = [(sort_key, sort_dir)] if sort_key else None)
        total = RingToneModel().collection().count()      
        
    return {'total' : total, 'items' : [item.export() for item in items]}


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@signature_required
@json_response
def scene_buy(request):
    spec = {
            'imsi' : '',
            'carrier' : '',
            'scene_id' : '',
            }
    params = extract_parameters(request, spec)
    if not params['imsi']:
        return HttpResponseBadRequest("Missing imsi")
    if not params['scene_id']:
        return HttpResponseBadRequest("Missing scene_id")
    
    ensure_user(params["imsi"], params['carrier'])
    buy_scene(params["imsi"], params['scene_id'])


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@signature_required
@json_response
def ringtone_buy(request):
    spec = {
            'imsi' : '',
            'carrier' : '',
            'ringtone_id' : '',
            }
    params = extract_parameters(request, spec)
    if not params['imsi']:
        return HttpResponseBadRequest("Missing imsi")
    if not params['ringtone_id']:
        return HttpResponseBadRequest("Missing ringtone_id")
    
    ensure_user(params["imsi"], params['carrier'])
    buy_ringtone(params['imsi'], params['ringtone_id'])


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def scene_user(request):
    spec = {
            'carrier' : '',
            'imsi' : '',
            }
    params = extract_parameters(request, spec)
    if params['carrier'] not in _CARRIERS:
        return HttpResponseBadRequest("Invalid carrier")
    if not params['imsi']:
        return HttpResponseBadRequest("Missing imsi")
        
    user = RingUserModel().find_one({"imsi" : params['imsi']})
    if user:
        scene_ids = [item['id'] for item in user['scenes']]
        items = get_scenes(params['carrier'], scene_ids)
    else:
        items = []
    return {'total' : len(items), 'items' : scenes_export(items, params['carrier'])}

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def ringtone_user(request):
    spec = {
            'imsi' : '',
            }
    params = extract_parameters(request, spec)
    if not params['imsi']:
        return HttpResponseBadRequest("Missing imsi")
        
    user = RingUserModel().find_one({"imsi" : params['imsi']})
    if user:
        ringtone_ids = [item['id'] for item in user['ringtones']]
        items = get_ringtones(ringtone_ids)
    else:
        items = []
    return {'total' : len(items), 'items' : [item.export() for item in items]}


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@signature_required
@json_response
def scene_remove(request):
    spec = {
            'imsi' : '',
            'scene_id' : '',
            }        
    params = extract_parameters(request, spec)
    if not params['imsi']:
        return HttpResponseBadRequest("Missing imsi")
    if not params['scene_id']:
        return HttpResponseBadRequest("Missing scene_id")  

    spec = {"imsi" : params['imsi']}
    modifier = {
                "$pop" : {
                           "scenes" : {
                                       "id" : params['scene_id'],
                                       }
                           }
                }
    RingUserModel().collection().update(spec, modifier)
    
@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@signature_required
@json_response
def ringtone_remove(request):
    spec = {
            'imsi' : '',
            'ringtone_id' : '',
            }        
    params = extract_parameters(request, spec)
    if not params['imsi']:
        return HttpResponseBadRequest("Missing imsi")
    if not params['ringtone_id']:
        return HttpResponseBadRequest("Missing ringtone_id")  

    spec = {"imsi" : params['imsi']}
    modifier = {
                "$pop" : {
                           "ringtones" : {
                                       "id" : params['ringtone_id'],
                                       }
                           }
                }
    RingUserModel().collection().update(spec, modifier)    
    

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def scene_recommend(request):
    spec = {
            'carrier' : '',
            'imsi' : '',
            }
    params = extract_parameters(request, spec)
    if params['carrier'] not in _CARRIERS:
        return HttpResponseBadRequest("Invalid carrier")
    
    user = RingUserModel().find_one({"imsi" : params['imsi']})
    tags = []
    user_scene_ids = []
    if user and user['scenes']:
        tags = user['scenes'][-1].get('tags', [])
        user_scene_ids = [scene['id'] for scene in user['scenes']]

    query = {
                "carrier" : params["carrier"],
                "id" : {"$nin" : user_scene_ids}
            }
    if tags:
        query["tags"] = {"$in": tags}
    items = RingSceneModel().find(query, limit = 100)

    random.shuffle(items)
    items = items[:4]

    return {'total': len(items), 'items' : scenes_export(items, params['carrier'])}


@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def search_hot(request):
    spec = {
            'carrier' : '',
            }
    params = extract_parameters(request, spec)
    if params['carrier'] not in _CARRIERS:
        return HttpResponseBadRequest("Invalid carrier")

    keys = {            
            "cm" : [u'领悟', u'趁早', u'存在', u'那些年', u'手掌心', u'时间煮雨', u'千千阙歌', u'不再联系', u'一万个舍不得'],
            "ct" : [u'领悟', u'趁早', u'存在', u'那些年', u'蓝莲花', u'时间煮雨', u'千千阙歌', u'不再联系', u'当我想你的时候', u'一万个舍不得'],
            "cu" : [u'领悟', u'趁早', u'存在', u'蓝莲花', u'手掌心', u'时间煮雨', u'千千阙歌', u'不再联系', u'当我想你的时候', u'一万个舍不得'],
           }
    return keys.get(params['carrier'], [])
    

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@signature_required
@json_response
def feedback(request):
    spec = {
            'user' : '',
            'content' : '',
            }
    params = extract_parameters(request, spec)
    if not (params['user'] and params['content']):
        return HttpResponseBadRequest("Missing parameter")
    
    data = RingFeedbackModel({
                       'user' : params['user'],
                       'content' : params['content'],
                       'time' : datetime.utcnow()
                       })
    RingFeedbackModel().collection().insert(data)
    

@perf_logged(logger = _LOGGER)
@exception_handled(logger = _LOGGER, retvalue_on_error = HttpResponseServerError())
@json_response
def startup_info(request):
    '''
    Must be first call for every client.
    Returns client update info, server time (for signature), etc.
    '''
    spec = {
        'channel' : '',
        }
    params = extract_parameters(request, spec)
    version_code = 2
    min_version_code = 2
    
    path = "ring/apk/funnyring.apk"
    local_path = os.path.join("/vol/www", path)    
    if os.path.exists(local_path):            
        size = os.path.getsize(local_path)
    else:
        size = 0
        
    url = "http://%s/" % STATIC_SERVER + path
    
    data = {
            "server_time" : datetime.utcnow(),
            "client_info" : {
                             "version_code" : version_code,
                             "url" : url,
                             "description" : u"铃声小蜜",
                             "size" : size,
                             "min_version_code" : min_version_code,
                             },
            "get_url" : "http://%s/geturl.html" % STATIC_SERVER,
            }
    
    return data

def get_ringback_ranklist(carrier):
    fields = ['title', 'type', 'image']
    ranks = RingBackRankModel().find(query = {"carrier" : carrier}, fields = fields)
    items = [filter_dct(rank, fields) for rank in ranks]
    for item in items:
        if item['title'].find(u"彩铃") == -1:
            item['title'] += u"彩铃"   
    return items

def get_ringtone_ranklist():
    fields = ['title', 'type', 'image']
    ranks = RingToneRankModel().find(query = {}, fields = fields)
    items = [filter_dct(rank, fields) for rank in ranks]
    return items


def get_scenes(carrier, ids):
    query = {
             'carrier' : carrier,
             '_id' : {'$in' : ids}
             }       
    scenes = RingSceneModel().find(query) if ids else []
    mapping = {}
    for scene in scenes:
        mapping[scene['_id']] = scene
    scenes = []
    for id in ids:
        scene = mapping.get(id)
        if scene:
            scenes.append(scene)
    return scenes

def get_ringbacks(carrier, ids):    
    mapping = get_ringbacks_map(carrier, ids)
    items = []
    for id in ids:
        item = mapping.get(id)
        if item:
            items.append(item)
    return items  

def get_ringtones(ids):
    mapping = get_ringtones_map(ids)
    items = []
    for id in ids:
        item = mapping.get(id)
        if item:
            items.append(item)
    return items

def get_ringbacks_map(carrier, ids):
    ringbacks = RingBackModel().find({"source" : carrier, "_id" : {"$in" : ids}}) if ids else []
    
    mapping = {}
    for ringback in ringbacks:
        mapping[ringback["_id"]] = ringback
    return mapping  

def get_ringtones_map(ids):
    ringtones = RingToneModel().find({"_id" : {"$in" : ids}}) if ids else []
    
    mapping = {}
    for ringtone in ringtones:
        mapping[ringtone['_id']] = ringtone
    return mapping    

def buy_scene(imsi, scene_id):
    scene = RingSceneModel().find_one({'_id' : scene_id})
    if not scene:
        return
    
    buy_ringtone(imsi, scene['ringtone'])
    #buy_ringback
    
    spec = {
                "imsi" : imsi,
                "scenes.id" : {"$ne" : scene_id},
            }
    modifier = {
                "$push" : {
                           "scenes" : {
                                       "id" : scene_id, 
                                       "tags" : scene['tags'],
                                       "buy_time" : datetime.utcnow()
                                       }
                           }
                }
    
    RingUserModel().collection().update(spec, modifier)

def buy_ringtone(imsi, ringtone_id):
    ringtone = RingToneModel().find_one({'_id' : ringtone_id})
    if not ringtone:
        return
    
    spec = {
                "imsi" : imsi,
                "rongtones.id" : {"$ne" : ringtone_id},
            }
    modifier = {
                "$push" : {
                           "ringtones" : {
                                       "id" : ringtone_id, 
                                       "tags" : ringtone['tags'],
                                       "buy_time" : datetime.utcnow()
                                       }
                           }
                }
    
    RingUserModel().collection().update(spec, modifier)


def scenes_export(scenes, carrier):
    '''
    return dict
    '''
    ringtone_ids= []
    ringback_ids = []
    for scene in scenes:
        if scene['ringtone']:
            ringtone_ids.append(scene['ringtone'])
        if scene['ringback']:
            ringback_ids.append(scene['ringback'])

    ringtones_map = get_ringtones_map(ringtone_ids)
    ringbacks_map = get_ringbacks_map(carrier, ringback_ids)
    
    items = []
    for scene in scenes:
        item = scene.export()
        ringtone = ringtones_map.get(item['ringtone'])
        ringback = ringbacks_map.get(item['ringback'])
        item['ringtone'] = ringtone.export() if ringtone else None
        item['ringback'] = ringback.export() if ringback else None
        if item['ringtone']:
            if carrier == 'cu' or item['ringback']:
                items.append(item)
    return items

def ensure_user(imsi, carrier):
    if not imsi:
        return
    
    if not RingUserModel().find_one({"imsi" : imsi}):
        try:
            RingUserModel().collection().insert(RingUserModel({"imsi" : imsi, "carrier" : carrier}))
        except Exception:
            pass
    

def filter_dct(dct, fields):
    if dct is None:
        return None
    
    item = {}
    for field in fields:
        item[field] = dct[field]
    return item


def parse_sort(sort):
    if sort.startswith("-"):
        sort_dir = -1
        key = sort[1:]
    else:
        sort_dir = 1
        key = sort
    return key, sort_dir
