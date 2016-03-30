# -*- coding: utf-8 -*-
import requests
import re
import urlparse
import HTMLParser
import json
import time
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoSourceModel, VideoItemModel

'''
channel： http://mobile.video.qq.com/fcgi-bin/dout_iphone?auto_id=1&platform=7&otype=json&version=20302
list：    http://mobile.video.qq.com/fcgi-bin/dout_iphone?auto_id=[channel_id]&itype=-1&iyear=-1&iarea=-1&iedition=-1&itrailer=0&icolumn=-1&sort=1&otype=json&platform=7&version=10800&page=0&pagesize=24
Album：   http://live.qq.com/json/ipad/cover/y/ygb2jrzixwffxlp.json
'''

CHANNELS = {
    14: {
        "c_eng_name": "movie",
        "c_list_param": {
            "itype": -1,
            "iyear": -1,
            "iarea": -1,
            "iedition": -1,
            "itrailer": -1,
            "sort": 2,
            "page": 0,
            "version": 10800
        },
        "c_name": u"电影",
    },
    15: {
        "c_eng_name": "tv",
        "c_list_param": {
            "itype": -1,
            "iyear": -1,
            "iarea": -1,
            "iedition": -1,
            "itrailer": -1,
            "sort": 2,
            "page": 0,
            "version": 10800
        },
        "c_name": u"电视剧",
    },
    16: {
        "c_eng_name": "cartoon",
        "c_list_param": {
            "itype": -1,
            "iyear": -1,
            "iarea": -1,
            "sort": 2,
            "page": 0,
            "version": 10500
        },
        "c_name": u"动漫",
    },
    17: {
        "c_eng_name": "variety",
        "c_list_param": {
            "itype": -1,
            "sort": 1,
            "page": 0,
            "version": 20100
        },
        "c_name": u"综艺",
    },
    # 18: {
    #     "c_eng_name": "music",
    #     "c_list_param": "igenre=-1&iyear=-1&iarea=-1&sort=1&page=0",
    #     "c_name": u"音乐",
    # },
    # 21: {
    #     "c_eng_name": "ent",
    #     "c_list_param": "itype=-1&sort=1&page=0",
    #     "c_name": u"娱乐",
    # },
    # 22: {
    #     "c_eng_name": "news",
    #     "c_list_param": {
    #         "itype": -1,
    #         "sort": 1,
    #         "page": 0
    #     },
    #     "c_name": u"新闻",
    # },
    # 23: {
    #     "c_eng_name": "finance",
    #     "c_list_param": "itype=-1&sort=1&page=0",
    #     "c_name": u"财经",
    # },
    # 24: {
    #     "c_eng_name": "live",
    #     "c_list_param": "",
    #     "c_name": u"直播",
    # },
    # 37: {
    #     "c_eng_name": "course",
    #     "c_list_param": "itype=-1&sort=1&page=0",
    #     "c_name": u"微讲堂",
    # },
    # 39: {
    #     "c_eng_name": "game",
    #     "c_list_param": "itype=-1&sort=1&page=0",
    #     "c_name": u"游戏",
    # },
    # 41: {
    #     "c_eng_name": "fashion",
    #     "c_list_param": "itype=-1&sort=1&page=0",
    #     "c_name": u"时尚",
    # },
    48: {
        "c_eng_name": "ustv",
        "c_list_param": {
            "itype": -1,
            "iyear": -1,
            "iarea": -1,
            "iedition": -1,
            "itrailer": -1,
            "sort": 2,
            "page": 0,
            "version": 10901
        },
        "c_name": u"美剧",
    },
    # 50: {
    #     "c_eng_name": "hollywood",
    #     "c_list_param": "itype=-1&iyear=-1&sort=2&page=0",
    #     "c_name": u"好莱坞会员",
    # },
    # 52: {
    #     "c_eng_name": "doc_cover",
    #     "c_list_param": "itype=-1&sort=1&page=0",
    #     "c_name": u"纪录片",
    # },
    # 54: {
    #     "c_eng_name": "sports_cover",
    #     "c_list_param": {
    #         "itype": -1,
    #         "icolumn": -1,
    #         "sort": 1,
    #         "page": 0
    #     },
    #     "c_name": u"体育",
    # },
    57: {
        "c_eng_name": "uktv",
        "c_list_param": {
            "itype": -1,
            "iyear": -1,
            "iarea": -1,
            "iedition": -1,
            "itrailer": -1,
            "sort": 2,
            "page": 0,
            "version": 10901
        },
        "c_name": u"英剧",
    },
    # 61: {
    #     "c_eng_name": "life",
    #     "c_list_param": "itype=-1&sort=1&page=0",
    #     "c_name": "生活",
    # },
    # 64: {
    #     "c_eng_name": "travel",
    #     "c_list_param": "itype=-1&sort=1&page=0",
    #     "c_name": "旅游",
    # },
    # 67: {
    #     "c_eng_name": "parenting",
    #     "c_list_param": "itype=-1&sort=1&page=0",
    #     "c_name": "母婴",
    # },
    69: {
        "c_eng_name": "funny",
        "c_list_param": {
            "itype": -1,
            "sort": 1,
            "page": 0,
            "version": 30000
        },
        "c_name": u"搞笑",
    }
}

SHORT_VIDEO = [u"搞笑"]

SERVER = "http://mobile.video.qq.com"

PARAMS_INFO = {
    'icolumn': -1,
    'sort': 1,  # 1:late 2:hot
    'appver': '2.6.0.4108',
    'sysver': 'ios7.0.4',
    'device': 'iPhone',
    'lang': 'en_US',
    'otype': "json",
    'platform': 7,
    'guid': 'aad6326c460a11e3b068abcd0889890a'
}


class ListCrawler(Crawler):

    type = "video.tencent.list"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        for key, data in CHANNELS.iteritems():
            Scheduler.schedule(
                ListCrawler.type,
                key=key,
                data=data,
                priority=conf.get('priority', Priority.High),
                interval=conf.get('interval', 3600)
            )

    def crawl(self):
        channel_id = self.key
        channel = self.data['c_name']
        list_params = self.data['c_list_param']
        page = list_params['page']
        pagesize = 24
        now = int(time.time())

        params = dict(list_params)  # list_params & PARAMS_INFO merge
        params.update(PARAMS_INFO)

        while True:
            list_data = api_list(
                auto_id=channel_id, page=page, pagesize=pagesize, params=params)
            if list_data['returncode'] != 404:
                if list_data.get('cover'):
                    for item in list_data["cover"]:
                        source_id = item.get("c_cover_id")
                        pubtime = item.get("c_year")
                        checkup_time = datetime.strptime(
                            item['c_checkup_time'], "%Y-%m-%d %H:%M:%S")
                        checkup_time = time.mktime(checkup_time.timetuple())

                        data = {
                            "source_id": source_id,
                            "title": item.get("c_title"),
                            "image": item.get("c_pic"),
                            "actors": item.get("c_actor"),
                            "directors": item.get("c_director"),
                            "categories": item.get("c_subtype"),
                            "channel": channel,
                            "region": item.get("c_area"),
                            "pubtime": pubtime,
                        }

                        Scheduler.schedule(
                            type=AlbumCrawler.type,
                            key=source_id,
                            data=data,
                            # checkup time whthin three hours set reset==True
                            reset=(now - checkup_time) < 10800
                        )
                    page += 1

                if list_data.get('video'):
                    for item in list_data["video"]:
                        source_id = item.get("c_vid")
                        pubtime = item.get("c_ctime")

                        data = {
                            "source_id": source_id,
                            "title": item.get("c_title"),
                            "image": item.get("c_pic"),
                            "channel": channel,
                            "pubtime": pubtime,
                        }

                        Scheduler.schedule(
                            type=AlbumCrawler.type,
                            key=source_id,
                            data=data,
                        )
                    page += 1
            else:
                return


class AlbumCrawler(Crawler):

    type = "video.tencent.album"

    '''
    http://v.qq.com/cover/[x]/[key]/xxxxxx.html
    http://v.qq.com/cover/[x]/[key].html
    '''
    @staticmethod
    def extract_key(url):
        for regex in ["^http://v.qq.com/cover/\w/(\w+)/\w+\.html$", "^http://v.qq.com/cover/\w/(\w+)\.html$"]:
            key = re.findall(regex, url)
            if key != []:
                return key[0]

    def crawl(self):
        album_id = self.key
        if self.data['channel'] in SHORT_VIDEO:
            url = "http://v.qq.com/page/%s/%s/%s/%s.html" % (
                album_id[0], album_id[1], album_id[-1], album_id)
            pubtime = datetime.strptime(
                self.data["pubtime"], "%Y-%m-%d %H:%M:%S")
            video = VideoItemModel({
                "title": self.data["title"],
                "url": url,
                "stream": [{
                           "url": "javascript:getUrl('tencent', '%s')" % url
                           }],
                "image": self.data["image"],
                "channel": self.data["channel"],
            })
            model = VideoSourceModel({
                                     "source": self.data["source"],
                                     "source_id": album_id,
                                     "title": self.data["title"],
                                     "url": url,
                                     "image": self.data["image"],
                                     "channel": self.data["channel"],
                                     "pubtime": pubtime,
                                     "videos": [video]
                                     })
            export(model)
            self.data['to_album_id'] = model['to_album_id']
        else:
            album_url = "http://v.qq.com/detail/%s/%s.html" % (
                album_id[0], album_id)
            album_data = api_album(album_id[0], album_id)
            if album_data['trailer'] == 1:
                play_url = "http://v.qq.com/prev/%s/%s" % (
                    album_id[0], album_id)
            else:
                play_url = "http://v.qq.com/cover/%s/%s" % (
                    album_id[0], album_id)
            description = album_data.get("columndesc")
            if not description:
                description = album_data.get("desc")
            description = "".join(description.split())
            try:
                pubtime = datetime.strptime(self.data.get("pubtime"), "%Y")
            except:
                pubtime = datetime.utcfromtimestamp(0)

            videos = []
            columnid = album_data.get('columnid')
            rely = album_data.get('rely')
            if columnid:  # columnid != 0
                for video_dict in rely:
                    for year, months in video_dict.iteritems():
                        for month in months:
                            videolist_id = "%s_%s" % (year, month)
                            videos_data = api_video(columnid, videolist_id)
                            for video in videos_data['items']:
                                time = video.get('date')
                                time = datetime.strptime(time, "%Y-%m-%d")
                                url = "http://v.qq.com/cover/%s/%s.html" % (
                                    video.get('coverid')[0], video.get('coverid'))
                                video = VideoItemModel({
                                    "title": video.get('sectitle'),
                                    "description": video.get('breif'),
                                    "url": url,
                                    "stream": [{
                                               "url": "javascript:getUrl('tencent', '%s')" % url
                                               }],
                                    "image": video.get('snapurl'),
                                    "time": time
                                })
                                videos.append(video)
            if not columnid:  # columnid == 0, only one video
                for video in album_data['videos']:
                    videos.append(clean_video(video, play_url))

            # self.data is not None: export(data)
            if self.data:
                model = VideoSourceModel({
                    "source": self.data.get('source'),
                    "source_id": album_id,
                    "title": album_data['columnname'] if album_data['columnname'] else self.data["title"],
                    "image": self.data.get("image"),
                    "url": album_url,
                    "actors": self.data.get("actors"),
                    "directors": self.data.get("directors"),
                    "categories": self.data.get("categories"),
                    "channel": self.data.get("channel"),
                    "region": self.data.get("region"),
                    "description": description,
                    "pubtime": pubtime,
                    "videos": videos,
                })
            # self.data is None: crawl web data first
            # (http://v.qq.com/cover/x/xxxxx.html), and export(data)
            else:
                hxs = load_html(play_url)
                channel = hxs.select(
                    "//div[@class='mod_crumbs']/a[1]/text()").extract()[0]
                album_hxs = hxs.select(
                    "//div[@class='mod_video_intro mod_video_intro_rich']")
                image = album_hxs.select("a/img/@src").extract()[0]
                title = album_hxs.select(
                    "div[@class='video_title']/strong/a/text()").extract()[0]
                directors = []
                for director_hxs in album_hxs.select("//div[@itemprop='director']/a"):
                    director = director_hxs.select("span/text()").extract()[0]
                    directors.append(director)
                actors = []
                for actor_hxs in album_hxs.select("//div[@itemprop='actors']/a"):
                    actor = actor_hxs.select("span/text()").extract()[0]
                    actors.append(actor)
                region = album_hxs.select(
                    "//div[@class='info_area']/span[@class='content']/a/text()").extract()[0]
                categories = []
                for categorie_hxs in album_hxs.select("//div[@class='info_category']/span[@class='content']/a"):
                    categorie = categorie_hxs.select("text()").extract()[0]
                    categories.append(categorie)
                pubtime = album_hxs.select(
                    "//div[@class='info_years']/span[@class='content']/a/text()").extract()[0]
                if re.match("^\d+$", pubtime):
                    pubtime = datetime.strptime(pubtime, "%Y")
                else:
                    pubtime = datetime.utcfromtimestamp(0)

                model = VideoSourceModel({
                    "source": self.data.get('source'),
                    "source_id": album_id,
                    "title": title,
                    "image": image,
                    "url": album_url,
                    "actors": actors,
                    "directors": directors,
                    "categories": categories,
                    "channel": channel,
                    "region": region,
                    "description": description,
                    "pubtime": pubtime,
                    "videos": videos,
                })
            export(model)
            self.data['to_album_id'] = model['to_album_id']


def call_api(path, params={}, retry=3):
    url = urlparse.urljoin(SERVER, path)

    retries = 0
    while True:
        try:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            data = re.findall("=(.+);$", resp.text)[0]
            data = json.loads(data)
            if data["returncode"] == 503:
                raise Exception("Call api failed - %s" % data)
            break
        except:
            retries += 1
            if retries >= retry:
                raise
            time.sleep(2)
    return data


def call_api2(path):
    server = "http://live.qq.com"
    params = {
        "appver": "2.7.1.2776",
        "sysver": "ios7.0.4",
        "device": "iPhone",
        "lang": "en_US"
    }
    url = urlparse.urljoin(server, path)
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def api_list(auto_id, page, pagesize, params):
    params['auto_id'] = auto_id
    params['page'] = page
    params['pagesize'] = pagesize
    return call_api("/fcgi-bin/dout_iphone", params)


def api_album(folder, album_id):
    return call_api2("/json/ipad/cover/%s/%s.json" % (folder, album_id))


def api_video(columnid, videolist_id):
    return call_api2("/json/ipad/columnrelate/%s/%s.json" % (columnid, videolist_id))


def clean_video(video, play_url):
    url = "%s/%s.html" % (play_url, video.get("vid"))
    new_video = VideoItemModel({
        "title": video.get("tt") + video.get("secondtitle"),
        "url": url,
        "stream": [{
                   "url": "javascript:getUrl('tencent', '%s')" % url
                   }],
        "image": video.get("screenshot"),
    })
    return new_video


def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text=data)

if __name__ == "__main__":
    # data = {
    #     "c_eng_name": "tv",
    #     "c_list_param": {
    #         "itype": -1,
    #         "iyear": -1,
    #         "iarea": -1,
    #         "iedition": -1,
    #         "itrailer": -1,
    #         "sort": 2,
    #         "page": 0,
    #         "version": 10800
    #     },
    #     "c_name": u"电视剧",
    # }
    # ListCrawler(key=15, data=data).crawl()
    data = {
        "source": "tencent",
        "pubtime": "2014-01-15 14:09:04",
        "to_album_id": "6c8196b268994965be3d2605e9a4c991",
        "title": "2014网易年会开场视频",
        "source_id": "k0124l6fx4a",
        "image": "http://vpic.video.qq.com/69709831/k0124l6fx4a_160_90_3.jpg",
        "channel": "搞笑"
    }
    AlbumCrawler(key="k0124l6fx4a", data=data).crawl()  # crawl Api data
    # AlbumCrawler(key="lmgmeej2f1j9sy3").crawl()  # crawl web data
    # AlbumCrawler.extract_key("http://v.qq.com/detail/4/40nwh0gdlv64gbw.html")
