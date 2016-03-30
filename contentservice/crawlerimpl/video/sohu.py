#coding=utf8
import requests
import urlparse
import re
import time
import HTMLParser
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, export, Scheduler, Priority
from contentservice.models.video import VideoSourceModel, VideoItemModel
from contentservice.utils import get_exception_info

SERVER = "http://api.tv.sohu.com"
API_KEY = "9854b2afa779e1a6bff1962447a09dbd"
'''
source    channel    area    =>    area
sohu    电影    香港        港台
'''

CHANNELS = {
               100: u"电影",
               101: u"电视剧",
               115: u"动漫",
               106: u"综艺",
             #  107: u"纪录片",
             #  121: u"音乐",
             #  119: u"教育",
               122: u"新闻", #一个专辑有很多新闻,且专辑title经常变,会干扰入库的合并算法
             #  112: u"娱乐",
             #  130: u"星尚",
             #  9004: u"搜狐出品",
             #  9003: u"VIP",
            }

class CategoryCrawler(Crawler):

    type = "video.sohu.category"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        for catecode in CHANNELS.keys():
            Scheduler.schedule(CategoryCrawler.type, key = str(catecode), data = {"catecode" : catecode}, priority = conf.get('priority', Priority.Normal), interval = conf.get('interval', 3600))

    def crawl(self):
        catecode = self.data["catecode"]
        last_updated = self.data.get("updated", datetime.min)
        current_updated = datetime.max
        max_time = last_updated

        page = 1
        pagesize = 20
        while True:
            try:
                data = api_albums(catecode, page, pagesize)
                for item in data["videos"]:
                    try:
                        sid = item.get('sid')
                        detail = api_album(sid) if sid else None
                        model = self.extract_model(item, detail)

                        if sid:
                            videos = self.get_videos(sid)
                            if model['channel'] in [u'综艺']: #reverse order for zongyi
                                videos = [video for video in reversed(videos)]
                        else:
                            video = VideoItemModel({
                                     "title" : model["title"],
                                     "image" : model["image"],
                                     "description" : model["description"],
                                     "time" : model["time"],
                                     "price" : model["price"],
                                     "duration" : model["duration"],
                                     "url" : model["url"]
                                     })
                            videos = [video]

                        model['videos'] = videos
                        export(model)

                        current_updated = model["time"]
                        if max_time < current_updated:
                            max_time = current_updated
                    except:
                        self.logger.warning(get_exception_info())

                if current_updated < last_updated:
                    break
                if page * pagesize >= data["count"]:
                    break
            except:
                self.logger.warning(get_exception_info())
            page += 1

        self.data["updated"] = max_time

    def get_videos(self, sid):
        page = 1
        pagesize = 20
        videos = []
        while True:
            data = api_videos(sid, page, pagesize)
            for item in data["videos"]:
                video = self.extract_video(item)
                videos.append(video)
            if page * pagesize >= data["count"]:
                break
            page += 1
        return videos

    def extract_model(self, item, detail = None):
        try:
            pubtime = datetime.strptime(str(detail.get("tv_year")), "%Y") if detail else None
        except:
            pubtime = None
        model = VideoSourceModel({
                 "source" : self.data['source'],
                 "source_id" : item.get("sid"),
                 "title" : detail.get("tv_name") if detail else item.get("albumTitle"),
                 "image" : detail.get("ver_big_pic") if detail else item.get("ver_big_pic"),
                 "image2" : detail.get("hor_big_pic") if detail else item.get("hor_big_pic"),
                 "description" : detail.get("tv_desc") if detail else item.get("tv_desc"),
                 "directors" : item["director"].split(";") if item.get("director") else [],
                 "actors" : item["main_actor"].split(";") if item.get("main_actor") else [],
                 "region" : item.get("area"),
                 "url" : detail["s_url"] if detail else item["s_url"],
                 "categories" : item["tv_cont_cats"].split(";") if item.get("tv_cont_cats") else [],
                 "time" : datetime.strptime(item.get('tv_application_time', '1970-01-01')[:10], "%Y-%m-%d"),
                 "price" : detail.get("fee") if detail else item.get("fee"),
                 "channel" : item["cname"],
                 "completed" : item["vcount"] >= item["totalSet"],
                 "visits" : self.extract_visits(item.get("albumPC")),
                 "score" : item.get("tv_score"),
                 "pubtime" : pubtime,
                 })
        return model

    def extract_video(self, item):
        item = item["map"]
        video = VideoItemModel({
                  "title" : item.get("tv_name"),
                  "image" : item.get("ver_big_pic"),
                  "description" : item.get("tv_desc"),
                  "duration" : int(item.get("time_length", "0")),
                  "url" : item.get("url_html5", item.get("tv_url")),
               #out of date!   "time" : datetime.strptime(item.get("update_time", "1970-01-01 00:00:00")[:19], "%Y-%m-%d %H:%M:%S"),
                  })

        playinfo = api_playinfo(item["tv_ver_id"])

        stream_nor = []
        stream_high = []
        stream_super = []
        stream_mobile = [{
                          "url" : playinfo.get("downloadurl", ""),
                          "size" : playinfo.get("file_size_mobile", 0),
                          "format" : "mp4",
                          }]

        if playinfo.get("url_nor_mp4"):
            urls = playinfo["url_nor_mp4"].split(",")
            durations = playinfo["clipsDuration_nor"]
            sizes = playinfo["clipsBytes_nor"]
            stream_nor = self.extract_stream(urls, durations, sizes)
        if playinfo.get("url_high_mp4"):
            urls = playinfo["url_high_mp4"].split(",")
            durations = playinfo["clipsDuration_high"]
            sizes = playinfo["clipsBytes_high"]
            stream_high = self.extract_stream(urls, durations, sizes)
        if playinfo.get("url_super_mp4"):
            urls = playinfo["url_super_mp4"].split(",")
            durations = playinfo["clipsDuration_super"]
            sizes = playinfo["clipsBytes_super"]
            stream_super = self.extract_stream(urls, durations, sizes)

        video["stream_low"] = stream_nor
        video["stream_high"] = stream_super
        #video["stream"] = stream_high
        video["stream"] = stream_mobile
        return video

    def extract_stream(self, urls, durations, sizes):
        stream = []
        try:
            for i in range(len(urls)):
                stream.append({
                               "url" : urls[i],
                               "duration" : durations[i],
                               "size" : sizes[i],
                               "format" : "mp4",
                               })
        except:
            pass
        return stream

    def extract_visits(self, albumpc):
        if not albumpc:
            return None
        visits = 0
        if isinstance(albumpc, (int, long)):
            visits = albumpc
        else:
            visits = int(re.sub("[^0-9]", "", albumpc))
            if albumpc.find(u"万") != -1:
                visits *= 10000
        return visits

    def adapt_time_str(self, time_str):
        try:
            if not time_str:
                return None
            time_str = time_str.strip(u'\u79d2')
            if u'\u5206' in time_str:
                t = int(time_str.split(u'\u5206')[0]) * 60 + int(time_str.split(u'\u5206')[1])
            elif u'\u79d2' in time_str:
                t = int(time_str)
            else:
                return None
            return t
        except Exception,e :
            self.logger.error(e)

class AlbumCrawler(Crawler):

    type = "video.sohu.album"

    """
    AlbumCrawler.extract_key('http://tv.sohu.com/20131102/n389418658.shtml')
    """
    @staticmethod
    def extract_key(url):
        if re.match("^http://tv.sohu.com/\d+/n\d+.shtml$", url):
            hxs = load_html(url)
            for s in hxs.select("/html/head/script"):
                try:
                    text = s.select("text()").extract()[0]
                    key = re.findall("var\s*playlistId\s*=\s*\"(\d+)\";", text)[0]
                    return key
                except:
                    pass

    def crawl(self):
        album_id = self.key
        channel = self.data["channel"]

        detail = api_album(album_id) if album_id else None

        title = detail["tv_name"]
        directors = detail["director"].split(";")
        actors = detail["actor"].split(";")
        region = detail["area"]
        categories = detail["tv_cont_cats"].split(";")
        ver_image = detail["ver_high_pic"]
        hor_image = detail["hor_high_pic"]
        url = detail["s_url"]
        description = detail["tv_desc"]

        # 视频导出的数据模型
        model = VideoSourceModel({
            "source" : self.data['source'],
            "source_id" : album_id,
            "title" : title,
            "url" : url,
            "directors" : directors,
            "actors" : actors,
            "region" : region,
            "categories" : categories,
            "channel" : channel,
            "description" : description,
            "image" : ver_image,
            "image2" : hor_image,
            })
        # 导出数据
        export(model)
        self.data['to_album_id'] = model['to_album_id']
        return

def crawl_top(type):
    type2js = {
                "movie" : "phb_mv_day_50",
                "tv" : "phb_tv_day_50",
                "zy" : "phb_variety_day_50",
                }

    url = "http://tv.sohu.com/frag/vrs_inc/%s.js" % type2js[type]

    data = requests.get(url).text
    data = re.match("var %s=(.+)" % type2js[type], data).group(1)
    data = eval(data)
    titles = [unicode(item['tv_name'], 'utf8') for item in data['videos']]
    return titles

def api_albums(catecode, page, pagesize, order = 1, year = "", cat = "", area = "", cid = 1):
    params = {
              "cateCode" : catecode,
              "page" : page,
              "pageSize" : pagesize,
              "o" : order,
              "year" : year,
              "cat" : cat,
              "area" : area,
              "c" : cid,
              }
    return call_api("search2/album.json", params)


def api_videos(sid, page, pagesize, playurls = 1, cid = 1):
    path = "set/list2/%s.json" % sid
    params = {
              "page" : page,
              "pagesize" : pagesize,
              "playurls" : playurls,
              "c" : cid,
              }
    return call_api(path, params)

def api_album(sid):
    path = "set/info2/%s.json" % sid
    return call_api(path)

def api_playinfo(vid):
    path = "video/playinfo/%s.json" % vid
    return call_api(path)

def call_api(path, params = {}, retry = 3):
    params["api_key"] = API_KEY
    params["plat"] = 6
    params["sver"] = "3.2.2"
    params["partner"] = 2

    url = urlparse.urljoin(SERVER, path)

    retries = 0
    while True:
        try:
            resp = requests.get(url, params = params)
            resp.raise_for_status()
            data = resp.json()
            if data["status"] != 200:
                raise Exception("Call api failed - %s" % data)
            break
        except:
            retries += 1
            if retries >= retry:
                raise
            time.sleep(2)
    return data["data"]

def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "gbk"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text = data)

if __name__ == "__main__":
#     data = api_playinfo(1223256)
#     data = api_album(5488003)
#     CategoryCrawler(key = "101", data = {"catecode" : 101, "source": "sohu"}).crawl()
    data = {
            "channel": "电视剧",
            "source": "sohu"
            }
    AlbumCrawler(key = "5943232", data = data).crawl()
#     AlbumCrawler.extract_key(url = "http://tv.sohu.com/20131101/n389349033.shtml")
