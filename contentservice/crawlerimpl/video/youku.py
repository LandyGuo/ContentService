# -*- coding: utf-8 -*-
import logging
import requests
import urlparse
import re
import HTMLParser
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, export, Priority, Scheduler
from contentservice.models.video import VideoSourceModel, VideoItemModel, VideoRankModel
from contentservice.utils import get_exception_info

'''
http://api.3g.youku.com/layout/android3_0/item_list?pid=0865e0628a79dfbb&guid=0&cid=97&image_hd=3&ob=1&pg=1

http://api.3g.youku.com/layout/android3_0/play/detail?pid=0865e0628a79dfbb&guid=0&id=cc00bdf8962411de83b1&format=5

http://api.3g.youku.com/shows/cc00bdf8962411de83b1/videos?pid=0865e0628a79dfbb&guid=0&fields=vid|titl|lim|is_new&pg=1&pz=24&order=1

http://api.3g.youku.com/v3/play/address?pid=0865e0628a79dfbb&guid=0&id=XNDgyMjc1NjI0&format=1,2,3,4,5,6,7,8
标清格式: flvhd, m3u8_flv, m3u8
超清格式: mp4, m3u8_mp4,
高清格式: m3u8_hd, hd2
'''

logger = logging.getLogger("contentservice")

SERVER = "http://api.3g.youku.com"
PID = "0865e0628a79dfbb"
GUID = "0"

PAGE_LIMIT = 10
CHANNELS = {
    # 84: u"纪录片",
    85: u"综艺",
    #  86: u"娱乐",
    #  87: u"教育",
    #  88: u"旅游",
    #  89: u"时尚",
    #  90: u"母婴",
    91: u"资讯",
    #  92: u"原创",
    94: u"搞笑",
    #  95: u"音乐",
    96: u"电影",
    97: u"电视剧",
    #  98: u"体育",
    #  99: u"游戏",
    100: u"动漫",
    #  102: u"广告",
    #  103: u"生活",
    #  104: u"汽车",
    #  105: u"科技",
}

MAIN_CHANNELS = {
    85: u"综艺",
    96: u"电影",
    97: u"电视剧",
    100: u"动漫",
}

FORMATS_NORMAL = [
    ("flvhd", "flv"),
    ("m3u8", "m3u8"),
    ("m3u8_flv", "m3u8"),
]
FORMATS_HIGH = [
    ("mp4", "mp4"),
    ("m3u8_mp4", "m3u8"),
]
FORMATS_HD = [
    ("hd2", "flv"),
    ("m3u8_hd", "m3u8"),
]


class CategoryCrawler(Crawler):

    type = "video.youku.category"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        for cid in CHANNELS.keys():
            Scheduler.schedule(CategoryCrawler.type, key=str(cid), priority=conf.get(
                'priority', Priority.High), interval=conf.get('interval', 3600))

    def crawl(self):
        cid = self.key
        channel = CHANNELS[int(cid)]
        page = 1
        pagesize = 30

        while 1:
            try:
                data = api_shows(cid, page, pagesize)
                if data is not None:
                    page += 1
                else:
                    return
            except:
                self.logger.warning(get_exception_info())
                continue

            if not data.get('results'):
                break
            for item in data['results']:
                try:
                    show_id = item['tid']
                    reset = (item['completed'] == 0)
                    data = {
                        'channel': channel,
                        'image': item.get('show_vthumburl_hd') if item.get('show_vthumburl_hd') else item.get('show_thumburl_hd'),
                        'image2': item.get('show_thumburl_hd')
                    }
                    Scheduler.schedule(
                        AlbumCrawler.type, key=show_id, data=data, reset=reset)
                except:
                    self.logger.warning(get_exception_info())


class AlbumCrawler(Crawler):
    type = "video.youku.album"

    '''
    mobile site:
    http://v.youku.com/v_show/id_[id].html?x
    '''
    @staticmethod
    def extract_key(url):
        if re.match("http://v.youku.com/v_show/id_\w+.html", url):
            hxs = load_html(url)
            for s in hxs.select("/html/head/script"):
                try:
                    text = s.select("text()").extract()[0]
                    key = re.findall("var\s*videoId\s*=\s*'(\d+)';", text)[0]
                    return key
                except:
                    pass

    def crawl(self):
        album_id = self.key
        channel = self.data.get('channel')

        if channel in CHANNELS.values():
            model = self.crawl_show(album_id)
            model['image'] = self.data.get('image')
            model['image2'] = self.data.get('image2')
            if channel:
                model['channel'] = channel

            videos = self.crawl_video(album_id)
            if channel == u'综艺':
                videos = [video for video in reversed(videos)]

            model['videos'] = videos
            export(model)
            self.data['to_album_id'] = model['to_album_id']

    def crawl_show(self, show_id):

        def parse_number(text):
            if not text:
                return 0
            text = re.sub("[^0-9\.]", "", text)
            return float(text)

        data = api_detail(show_id)
        detail = data['detail']

        try:
            pubtime = datetime.strptime(
                detail.get('showdate', '1970-01-01').replace("-00", "-01"), "%Y-%m-%d")
        except:
            pubtime = None

        if detail['cats'] in MAIN_CHANNELS.values():
            model = VideoSourceModel({
                'source': self.data['source'],
                'source_id': detail['showid'],
                'url': "http://www.youku.com/show_page/id_z%s.html" % detail['showid'],
                'title': detail['title'],
                'duration': None,
                'visits': parse_number(detail.get('total_vv')),
                'comments': parse_number(detail.get('total_comment')),
                'score': parse_number(detail.get('reputation')),
                'favorites': parse_number(detail.get('total_fav')),
                'image': detail['img'],
                'region': detail['area'][0] if detail.get('area') else None,
                'categories': detail.get('genre', []),
                'description': detail.get('desc'),
                'completed': detail.get('completed') == 1,
                'actors': detail.get('performer', []),
                'directors': detail.get('director', []),
                #'price' : 0.0,
                'pubtime': pubtime,
                'channel': detail.get('cats', '')
            })
        else:
            model = VideoSourceModel({
                'source': self.data['source'],
                'source_id': show_id,
                'url': "http://v.youku.com/v_show/id_%s.html" % show_id,
                'title': detail['title'],
                'duration': None,
                'visits': parse_number(detail.get('total_vv')),
                'comments': parse_number(detail.get('total_comment')),
                'score': parse_number(detail.get('reputation')),
                'favorites': parse_number(detail.get('total_fav')),
                'image': detail['img'],
                'region': detail['area'][0] if detail.get('area') else None,
                'categories': detail.get('genre', []),
                'description': detail.get('desc'),
                'completed': detail.get('completed') == 1,
                'actors': detail.get('performer', []),
                'directors': detail.get('director', []),
                #'price' : 0.0,
                'pubtime': pubtime,
                'channel': detail.get('cats', '')
            })
        return model

    def crawl_video(self, show_id):
        videos = []
        page = 1
        pagesize = 30
        while True:
            data = api_videos(show_id, page, pagesize)
            if not data['results']:
                break

            for item in data['results']:
                try:
                    video = VideoItemModel({
                        "title": item['title'],
                        "source_id": item['videoid'],
                        "url": "http://v.youku.com/v_show/id_%s.html" % item['videoid'],
                    })

                    jsurl = "javascript: getUrl('youku', '%s')" % item[
                        "videoid"]
                    video["stream"] = [{"url": jsurl}]

                    # TODO:
#                     ret = api_plays(item['videoid'])
#                     results = ret.get('results', {})
#                     for key, fmt in FORMATS_NORMAL:
#                         if results.get(key):
#                             video["stream_low"] = self.extract_stream(results[key], fmt)
#                             break
#                     for key, fmt in FORMATS_HIGH:
#                         if results.get(key):
#                             video["stream"] = self.extract_stream(results[key], fmt)
#                             break
#                     for key, fmt in FORMATS_HD:
#                         if results.get(key):
#                             video["stream_high"] = self.extract_stream(results[key], fmt)
#                             break

                    videos.append(video)
                except:
                    self.logger.warning(get_exception_info())

            if pagesize * page >= data['total']:
                break
            page += 1
        return videos

    def extract_stream(self, result, fmt):
        stream = []
        if not result:
            return stream
        for item in result:
            stream.append({
                          'url': item['url'],
                          'size': item['size'],
                          'duration': item['seconds'],
                          'format': fmt,
                          })
        return stream


TOP_SPECS = [{
    "url": "http://movie.youku.com/top/",
    "type": "movie.day.youku",
            "title": u"优酷电影日榜",
},
    {
        "url": "http://tv.youku.com/top/",
        "type": "tv.day.youku",
        "title": u"优酷电视剧日榜",
    },
    {
        "url": "http://zy.youku.com/top/",
        "type": "zy.day.youku",
        "title": u"优酷综艺日榜",
    }
]


class TopCrawler(Crawler):
    type = "video.youku.top"
    recursive = True
    interval = 86400

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority=conf.get(
            'priority', Priority.High), interval=conf.get('interval', 3600))

    def crawl(self):
        for spec in TOP_SPECS:
            titles = crawl_top(spec["url"])
            rank = VideoRankModel({
                "source": self.data['source'],
                "type": spec["type"],
                "title": spec["title"],
                "videos": titles,
            })
            export(rank)


def crawl_top(url):
    resp = requests.get(url)
    resp.raise_for_status()
    hxs = HtmlXPathSelector(text=resp.text)
    titles = hxs.select(
        "//div[@class='sRank_W']/.//td[@class='show_title']/a/text()").extract()
    return titles


def call_api(path, params={}):
    params["pid"] = PID
    params["guid"] = GUID
    url = urlparse.urljoin(SERVER, path)
    resp = requests.get(url, params=params)
    return resp.json()


def api_shows(cid, page=1, pagesize=30, order=1):
    params = {
        "cid": cid,
        "image_hd": 3,
        "ob": order,
        "pg": page,
        "pz": pagesize
    }
    return call_api("layout/android3_0/item_list", params)


def api_detail(show_id):
    params = {
        "id": show_id,
        "format": 5,
    }
    return call_api("layout/android3_0/play/detail", params)


def api_videos(show_id, page=1, pagesize=30, order=1):
    params = {
        "fields": "vid|titl|lim|is_new",
        "pg": page,
        "pz": pagesize,
        "order": order
    }
    path = "shows/%s/videos" % show_id
    return call_api(path, params)


def api_plays(video_id):
    params = {
        "id": video_id,
        #1-mp4, 3-flv, 5-flvhd, 6-m3u8, 7-hd2
        "format": "1,2,3,4,5,6,7,8",
    }
    path = "v3/play/address"
    return call_api(path, params)


def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf8"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text=data)

if __name__ == "__main__":
    for key in CHANNELS.iterkeys():
        CategoryCrawler(key=key).crawl()
#     CategoryCrawler().crawl_video("0be44a68f05111e28b3f")
#     AlbumCrawler(key="f2d7cbbc510311e38b3f", data={
#                  "channel": u"电视剧", "source": "youku"}).crawl()
#     AlbumCrawler.extract_key(url = "http://v.youku.com/v_show/id_XNTkyMzk5NjI4.html")
