#coding=utf8
import codecs, os, random, shutil, pdb, re, subprocess
from contentservice.models.video import VideoSourceModel
from contentservice.crawler import export
from pymongo import MongoClient, Connection
from models.ring import RingSceneModel, RingToneModel, RingBackModel, RingSceneRankModel, RingBackRankModel
from django.conf import settings

def crawlerservice(command):
    from crawlerservice import CrawlerService
    service = CrawlerService(settings.CRAWLER_PID)
    if command == "start":
        service.start()
    elif command == "stop":
        service.stop()
    elif command == "restart":
        service.restart()
    elif command == "status":
        service.status()

def monitorservice(command):
    from monitor import service
    service(command)

def video_monitor():
    print 'run monitor'    
    from utils.video_monitor.run_monitor import run
    run()

def import_scene(path, carrier):

    def load_icon(filename):
        if not filename:
            return None

        iconpath = os.path.join(os.path.dirname(path), filename)
        shutil.copy(iconpath, os.path.join(settings.STATIC_BASE, "ring/image/scene"))
        return "http://%s/ring/image/scene/%s" % (settings.STATIC_SERVER, filename)

    for line in codecs.open(path, encoding="utf8").readlines():
        line = line.strip()

        try:
            title, icon, icon_inactive, ringtone, ringtone_price, ringback, ringback_price, scene_price, visits, tags = line.split("\t")

            icon = load_icon(icon)
            icon_inactive = load_icon(icon_inactive)

            tags = [t.strip() for t in tags.split(",")]
            data = RingSceneModel({
                                   "source" : "dolphin",
                                   "carrier" : carrier,
                                   "authority" : 10,
                                   "title" : title.strip(),
                                   "icon" : icon,
                                   "icon_inactive" : icon_inactive,
                                   "ringback" : ringback,
                                   "ringtone" : ringtone,
                                   "visits" : visits,
                                   "tags" : tags,
                                   "price" : float(scene_price) if scene_price else None,
                                   })
            data.on_import()

            if ringtone_price:
                RingToneModel().collection().update({"key" : ringtone}, {"$set" : {"price" : ringtone_price}})

        except Exception, e:
            print "Error %s. Line = %s" % (e, line)
            raise

def import_scene_rank(path, type, carrier):
    keys = []
    for line in codecs.open(path, encoding = "utf8").readlines():
        key = line.strip()
        keys.append(key)

    data = RingSceneRankModel({
                        "source" : "dolphin",
                        "carrier" : carrier,
                        "authority" : 10,
                        "title" : type,
                        "type" : type,
                        "scenes" : keys,
                        })
    data.on_import()


def import_ringback_rank(path, type):
    keys = []
    for line in codecs.open(path, encoding = "utf8").readlines():
        line = line.strip()
        if line.find("#") != -1:
            title, artist = line.split("#")
            key = RingBackModel({'title': title, 'artist' : artist})['key']
        keys.append(key)

    for carrier in ['ct', 'cm', 'cu']:
        item = RingBackRankModel({
                            "source" : "dolphin",
                            "authority" : 10,
                            "carrier" : carrier,
                            "type" : type,
                            #"title" : rank_title,
                            "ringbacks" : keys,
                            })
        item.on_import()


def random_visits(max_visits = 1000000, factor = 100.0):
    visits = int((factor/(factor - random.random() * (factor - 1)) - 1) / factor * max_visits)
    return visits

def show_scene_expires():
    for scene in RingSceneModel().find():
        ringback_id = scene.ringback
        if not ringback_id:
            continue
        ringback = RingBackModel().find_one({'id' : ringback_id})
        if not ringback:
            continue
        expires = ringback.expires.strftime('%Y-%m-%d')
        print '%s\t%s\t%s' % (scene.carrier, scene.title, expires)

def tar_txt():
    pdb.set_trace()

    basepath = "/vol/www/static/novel/txt"
    for dir1 in range(256):
        for dir2 in range(256):
            path = os.path.join(basepath, "%.2x/%.2x" % (dir1, dir2))
            if not os.path.exists(path):
                continue

            os.chdir(path)
            for name in os.listdir(path):
                if os.path.isfile(name):
                    continue
                try:
                    srcfile = name
                    tarfile = srcfile + ".tar.gz"
                    cmd = "tar -czf '%s' '%s'" % (tarfile, srcfile)
                    subprocess.call(cmd, shell = True)
                    shutil.rmtree(srcfile)
                    print tarfile
                except Exception, e:
                    print e


def import_douban():
    from contentservice.utils.datetimeutil import parse_date
    from contentservice.settings import MONGO_CONN_STR
    db = MongoClient(MONGO_CONN_STR).douban

    pdb.set_trace()

    def clean_title(title):
        zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
        if zhPattern.search(title):
            return title.split(" ")[0]
        else:
            return title

    for item in db.album.find():
        pubtime = None
        if item['pub_time']:
            pubtime = parse_date(re.sub("\(.*\)", "", item['pub_time'][0]))

        model = VideoSourceModel({
                         "title" : clean_title(item['title']),
                         "categories" : item['sub_category'],
                         "image" : item["img"],
                         "related" : item["related"],
                         "score" : item["score"],
                         "actors" : item["actors"],
                         "region" : item["area"][0] if item["area"] else None,
                         "url" : item["url"],
                         "description" : item["description"],
                         "pubtime" : pubtime,
                         "channel" : u"电影",
                         "source" : "douban",
                         "source_id" : re.findall("/(\d+)/", item['url'])[0],
                         })
        model.on_import()
        print model['title']

def import_mtime():
    from datetime import datetime
    from contentservice.models.video import VideoSourceModel
    from contentservice.settings import MONGO_CONN_STR
    from contentservice.utils.datetimeutil import parse_date
    db = MongoClient(MONGO_CONN_STR).mtime
    pdb.set_trace()

    for item in db.album.find():
        area = item["area"] if item.get("area") else None
        if isinstance(area, list):
            area = area[0]
        categories = item.get("type")
        if isinstance(categories, basestring):
            categories = [categories]
        description = item.get("description")
        if isinstance(description, list):
            description = "\n".join(description)
        tags = item.get("tags")
        if isinstance(tags, basestring):
            tags = [tags]
        channel = ""
        if item.get("category_id") == "1":
            channel = u"电影"
        elif item.get("category_id") == "0":
            channel = u"电视剧"
        try:
            model = VideoSourceModel({
                                    "source" : "mtime",
                                    "source_id" : item["id"],
                                    "title" : item["title"],
                                    "description" : description,
                                    "tags" : tags,
                                    "time" : datetime.strptime(item["create_time"], "%Y-%m-%d %H:%M:%S"),
                                    "duration" : item.get("duration"),
                                    "region" : area,
                                    "directors" : item.get("directors"),
                                    "score" : item.get("score"),
                                    "actors" : item.get("actors"),
                                    "categories" : categories,
                                    "channel" : channel,
                                    "url" : "http://movie.mtime.com/%s/" % item["id"],
                                    "pubtime" : parse_date(item["release_time"]),
                                      })
            model.on_import()
        except Exception, e:
            print e
        print model["title"]


def import_all_videos():
    from contentservice.models.video import VideoSourceModel
    from contentservice.settings import MONGO_CONN_STR
    db = MongoClient(MONGO_CONN_STR).content_video

    pdb.set_trace()
    for item in db.video.source.find(sort = [("updated", 1)]):
        model = VideoSourceModel(item)
        model.on_import()
        print model["title"]


def video_kpi():
    from contentservice.models.video import VideoAlbumModel, VideoChapterModel
    pdb.set_trace()

    valid_ids = set()
    for item in VideoChapterModel().collection().find({}, {"album_id" : True}):
        valid_ids.add(item["album_id"])

    for channel in [u"电影", u"电视剧", u"综艺", u"动漫", u"搞笑", u"擦边", u"音乐"]:
        print channel
        ids = set()
        for item in VideoAlbumModel().collection().find({"channel" : channel}, {"_id" : True}):
            ids.add(item["_id"])

        empty_ids = list(ids - valid_ids)
        total = VideoAlbumModel().collection().find({"channel" : channel}).count() - len(empty_ids)
        for field, defvalue in VideoAlbumModel.FIELDS.iteritems():
            if field in ["_id", "created", "updated", "deleted", "price", "completed", "authorities", "source", "channel"]:
                continue
            count = total - VideoAlbumModel().collection().find({field : defvalue, "channel" : channel, "_id" : {"$nin" : empty_ids}}).count()
            print "%s\t%s\t%s\t%s" % (field, count, total, count * 100.0/ total)

def update_region():
        conn = Connection()
        db = conn.content_video2
        count = 1
        source_videos =  db.video.source.find()
        for source_video in source_videos:
            model = VideoSourceModel({
                        "videos": source_video['videos'],
                        "image": source_video['image'],
                        "related": source_video['related'],
                        "duration": source_video['duration'],
                        "title": source_video['title'],
                        "comments": source_video['comments'],
                        "source": source_video['source'],
                        "score": source_video['score'],
                        "actors": source_video['actors'],
                        "price": source_video['price'],
                        "channel": source_video['channel'],
                        "description": source_video['description'],
                        "tags": source_video['tags'],
                        "deleted": source_video['deleted'],
                        "completed": source_video['completed'],
                        "visits": source_video['visits'],
                        "favorites": source_video['favorites'],
                        "authorities": source_video['authorities'],
                        "categories": source_video['categories'],
                        "created": source_video['created'],
                        "url": source_video['url'],
                        "region": source_video['region'],
                        "directors": source_video['directors'],
                        "pubtime": source_video['pubtime'],
                        "time": source_video['time'],
                        "source_id": source_video['source_id']
                        })
            export(model)
            count += 1
            print "count = %s" % count
        print "count = %s" % count
        print "map complete."

'''
Created on Nov 18, 2013

@author: lxwu
'''
import urllib
import uuid
import pymongo

SOURCE = ['sohu', 'youku']

def load_img(dir, url, source):
    file_name = "%s_%s.jpg" % (source, uuid.uuid4().hex)
    path = os.path.join(dir, file_name)
    try:
        f = open(path,'wb')
        f.write(urllib.urlopen(url).read())
        f.close()
    except:
        print "write error"
        pass

def img_urls(source):
    conn = pymongo.Connection()
    db = conn.content_video3
    image_list = db.video.album.find({"source": source}).distinct("image")
    return image_list

def img_count(channel, source):
    conn = pymongo.Connection()
    db = conn.content_video
    count = db.video.album.find({"source": source, "channel": channel}).count()
    return count

def sources():
    conn = pymongo.Connection()
    db = conn.content_video
    source_list = db.video.album.find().distinct("source")
    return source_list

if __name__ == "__main__":
    '''
    分类映射救数据
    '''
    update_region()
    '''
    下载数据到本地
    dir: 保存图片绝对路径
    '''
#     dir = "/home/lxwu/image"
#     for source in SOURCE:
#         image_url = img_urls(source)
#         for url in image_url:
#             load_img(dir, url, source)
