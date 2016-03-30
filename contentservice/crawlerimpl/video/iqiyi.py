# -*- coding: utf-8 -*-
import requests
import urllib
import json
import re
import os
import HTMLParser
import time
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from hessian.client import HessianProxy
from contentservice.models.video import VideoSourceModel, VideoItemModel, VideoRankModel
from contentservice.crawler import Crawler, export, Priority, Scheduler
from contentservice.utils import get_exception_info, pathutil
from contentservice.utils.datetimeutil import unix_time
from contentservice.settings import STATIC_BASE

_V_FILE = os.path.join(STATIC_BASE, "video/js/iqiyi.js")

_API_PATH = 'http://iface2.iqiyi.com/php/xyz/iface/?'

PARAMS_PROTOTYPE = {
    'key': 'f0f6c3ee5709615310c0f053dc9c65f2',
    'did': 'a14c1c4947791f11',
    'type': 'json',
    'id': '',
    'deviceid': '',
    'version': '4.8.1',
    'os': '7.0.4',
    'ua': 'iPad2,5',
    'network': 1,
    'screen_status': 2,
    'udid': '848b636d44f015623c170530e979a06932d48f0f',
    'ss': 2,
    'ppid': '',
    'uniqid': '0f607264fc6318a92b9e13c65db7cd3c',
    'openudid': '848b636d44f015623c170530e979a06932d48f0f',
    'idfv': 'F358B691-A82E-417B-9548-406BB644EEE3',
    'idfa': '39E4C4A4-FE55-42F7-9D14-269EE299F9E9',
}

PARAMS_LIST = {
    'f': 0,
    'ps': 36,
    'pn': 1,
    's': 5,  # 5: 新上线, 0: 热播榜, 4: 好评榜
    'up_tm': '',
    'pcat': 2,
    'ver_field': 0
}

PARAMS_ALBUM = {
    'getother': 0,
    'ad': 2,
    'nd': 0,
    'vs': '(null)',
    'vt': '(null)'
}

_CHANNEL_DCT = {
    1: u'电影',
    2: u'电视剧',
    #  3: u'纪录片',
    4: u'动漫',
    #  5: u'音乐',
    6: u'综艺',
    #  7: u'娱乐',
    #  9: u'旅游',
    #  10: u'片花',
    #  11: u'公开课',
    #  12: u'教育',
    #  13: u'时尚',
    16: u'微电影',
    #  17: u'体育',
    #  20: u'广告',
    #  21: u'生活',
    22: u'搞笑',
    #  102: u'爱奇艺出品',
}

_CHANNEL_PINYIN = {
    u"电影": "dianying",
    u"综艺": "zongyi",
    u"电视剧": "dianshiju",
    u"动漫": "dongman",
    u"微电影": "weidianying",
    u"搞笑": "fun",
}


class CategoryCrawler(Crawler):

    type = "video.iqiyi.category"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        for id in _CHANNEL_DCT.iterkeys():
            Scheduler.schedule(CategoryCrawler.type, key=str(id), data={"cid": id}, priority=conf.get(
                'priority', Priority.High), interval=conf.get('interval', 3600))

    def crawl(self):
        cid = self.data['cid']
        current_time = int(time.time())

        for album_data in self.get_albums(cid):
            try:
                album = extract_album(album_data, self.data['source'])
                if not album:
                    continue
                checkup_time = time.mktime(album['time'].timetuple())

                # can't get video for paid item
                if (not album["price"]) and album.get('source_id'):
                    Scheduler.schedule(
                        type=AlbumCrawler.type,
                        key=album['source_id'],
                        data={"time": album["time"]},
                        reset=(current_time - checkup_time) < 86400
                    )
            except:
                self.logger.warning(get_exception_info())

        self.data['updated'] = current_time

    def get_categories(self):
        params = PARAMS_PROTOTYPE.copy()
        params['category_id'] = 0
        ret = call_api("getCategoryTagsAndKeywords", params)
        keys = {}
        for id, lst in ret.preset_keys.iteritems():
            for s in lst:
                words = s.split(":")
                if len(words) == 2:
                    keys[words[0]] = words[1]
        return ret

    def get_albums(self, cid):
        cid = "%s,0~0~0" % cid

        params = dict(PARAMS_PROTOTYPE)
        params.update(PARAMS_LIST)
        params['category_id'] = cid

        while True:
            try:
                ret = call_api("getViewObject", params)
                if not ret.albumIdList:
                    break
                # list[0] is ordered by time, list[1] is recommendation
                ids = ret.albumIdList[0]['idlist']
                if not ids:
                    break
                for album_id in ids:
                    album = ret.albumArray.get(int(album_id))
                    if album:
                        yield album
            except GeneratorExit:
                return
            except:
                self.logger.warning(get_exception_info())
                continue
            params['pn'] += 1


class AlbumCrawler(Crawler):

    type = "video.iqiyi.album"

    """
    AlbumCrawler.extract_key('http://www.iqiyi.com/v_[key].html')
    http://www.iqiyi.com/a_19rrgj9hzd.html
    url : http://www.iqiyi.com/dongman/20120803/71eec512642bf3d6.html #动漫
    url : http://www.iqiyi.com/dianying/20120815/16cf2101802c2a81.html #电影
    url : http://www.iqiyi.com/edu/20130514/cc8dfe2e720534ba.html
    """
    @staticmethod
    def extract_key(url):
        for regex in ["^http://www.iqiyi.com/[a-z]+/\d+/[0-9a-z]+.html$", "^http://www.iqiyi.com/v_[0-9a-z]+.html$"]:
            prog = re.compile(regex)
            if re.match(prog, url):
                hxs = load_html(url)
                key = hxs.select(
                    "//div[@id='flashbox']/@data-player-albumid").extract()[0]
                return key

    def crawl(self):
        album_id = self.key

        params = dict(PARAMS_PROTOTYPE)
        params.update(PARAMS_ALBUM)

        ret = call_api("getAlbum", params, [
                       album_id, None, None, album_id, None, '1', '0'])

        if ret._id != album_id:
            return

        model = extract_album(ret, self.data['source'])

        videos = []
        if ret.tv['block']:
            block = ret.tv['block']
            for block_index in xrange(len(ret.tv['block'])):
                if block_index != 0:
                    block_now = block[block_index]
                    ret = call_api("getAlbum", params, [
                                   album_id, None, None, None, '1', '1', block_now])
                videos.extend(self.extract_videos(
                    album_id, ret.tv['other']))
        if not ret.tv['block']:
            videos.extend(
                self.extract_videos(album_id, ret.tv['other']))

        model['videos'] = videos
        export(model)
        self.data['to_album_id'] = model['to_album_id']

    def extract_videos(self, album_id, tv_other):
        videos = []
        for index in xrange(len(tv_other)):
            line = tv_other[index]
            # 315195~434532~爱情自有天意第84集~84~~http://pic9.qiyipic.com/thumb/20130322/v434532_160_90.jpg~~~~
            words = line.split("~")
            for word in words:
                m = re.match("^(\d+)$", word)
                if m:
                    if words[0] != words[1]:
                        album_id = words[0]
                        word = words[1]
                    video = self.get_video(album_id, word)
                    if not video:
                        continue
                    if video:
                        videos.append(video)
                        break
        return videos

    def get_video(self, album_id, video_id):
        album_id = str(album_id)
        video_id = str(video_id)

        params = dict(PARAMS_PROTOTYPE)
        params.update(PARAMS_ALBUM)

        try:
            ret = call_api("getAlbum", params, [
                           album_id, None, None, video_id, None, '1', '0'])
            if not ret.tv[0]._id or ret.tv[0]._id != video_id:
                ret = call_api("getAlbum", params, [
                               video_id, None, None, None, '1', '0'])
        except:
            self.logger.warning(get_exception_info())
            return

        for i in range(ret.tv['count']):
            if ret.tv[i]._id == video_id:
                return extract_video(ret.tv[i])
        raise Exception("No video found for video_id = %s" % video_id)


class VCrawler(Crawler):
    type = "video.iqiyi.v"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        Scheduler.schedule(VCrawler.type, priority=conf.get(
            'priority', Priority.High), interval=conf.get('interval', 600))

    def crawl(self):
        album_id = 203409200
        video_id = 203409200
        params = PARAMS_PROTOTYPE.copy()
        params['category_id'] = 0
        params['screen_status'] = 0
        ret = call_api("getAlbum", params, [
                       album_id, None, None, video_id, '1', '1', '0'])
        url = ret.tv[0].res[0].url
        v = re.findall("v=(\d+)", url)[0]

        js = "var iqiyi_v=%s;" % v
        pathutil.ensure_dir(_V_FILE)
        with open(_V_FILE, "w") as fp:
            fp.write(js)


TOP_SPECS = [
    {
        "cid": 1,
        "title": u"爱奇艺电影日榜",
        "type": "movie.day.iqiyi",
    },
    {
        "cid": 2,
        "title": u"爱奇艺电视剧日榜",
        "type": "tv.day.iqiyi",
    },
    {
        "cid": 6,
        "title": u"爱奇艺综艺日榜",
        "type": "zy.day.iqiyi",
    }
]


class TopCrawler(Crawler):

    '''
    http://top.iqiyi.com/dianshiju.html
    '''
    type = "video.iqiyi.top"
    recursive = True
    interval = 86400

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority=conf.get(
            'priority', Priority.High), interval=conf.get('interval', 0))

    def crawl(self):
        for spec in TOP_SPECS:
            titles = crawl_top(spec["cid"])

            rank = VideoRankModel({
                                  "source": self.data['source'],
                                  "type": spec["type"],
                                  "title": spec["title"],
                                  "videos": titles
                                  })
            export(rank)


def crawl_top(cid):
    timestamp = unix_time() * 1000
    url = "http://top.inter.qiyi.com/index/front"
    var = "tab%s" % timestamp
    params = {
        "cid": cid,
        "dim": "wee",
        "len": 50,
        "area": "top",
        "cb": var,
        "time": timestamp,
    }
    resp = requests.get(url, params=params)
    data = re.match("var %s=(\{.+\}$)" % var, resp.text).group(1)
    data = json.loads(data)
    titles = []
    for item in data["data"]:
        titles.append(item["album_name"])
    return titles


def call_api(method, params={}, args=[]):
    url = _API_PATH + urllib.urlencode(params)
    hp = HessianProxy(url)
    ret = hp(method, args)
    return ret


def extract_album(album, source):
    if hasattr(album, "_a"):
        album = album._a

    channel = _CHANNEL_DCT.get(int(album._cid), '')

    channel_py = _CHANNEL_PINYIN.get(channel)
    if channel_py:
        url = "http://m.iqiyi.com/%s/a/%s.html" % (channel_py, album._id)
    else:
        url = ""

    pubtime = album.year
    if len(pubtime) == 4:
        pubtime = datetime.strptime(pubtime, "%Y")
    elif len(pubtime) == 8:
        pubtime = datetime.strptime(pubtime, "%Y%m%d")
    else:
        pubtime = None

    visits = getattr(album, 'vv')
    m = re.match("^\d+$", getattr(album, 'vv'))
    if m:
        visits = int(visits) * 10000
    else:
        visits = int(visits[:-1]) * 10000

    item = VideoSourceModel({
        'source': source,
        'source_id': album._id,
        'url': url,
        'title': album.clm if hasattr(album, 'clm') and album.clm else album._t,
        'duration': int(album._dn),
        'visits': visits,
        'score': float(album._sc),
        'image': album._img,
        'tags': album.tag.split() if hasattr(album, "tag") else [],
        'channel': channel,
        'description': album.desc if hasattr(album, "desc") else "",
        'price': float(album.t_pc),
        'directors': album._da.split(",") if hasattr(album, "_da") else [],
        'actors': album._ma.split(",") if hasattr(album, "_ma") else [],
        # last update time for iqiyi
        'time': datetime.strptime(getattr(album, "fst_time", "1970-01-01"), "%Y-%m-%d"),
        'price': 0.0,
        'pubtime': pubtime,
    })

    return item


def extract_video(video):
    m = re.match(".+/(.+).(?=m3u8|mp4)", video.res[len(video.res) - 1].vid)
    if m:
        vid = m.group(1)
    else:
        raise Exception("No vid found.")

    item = VideoItemModel({
        'url': "http://m.iqiyi.com/play.html?tvid=%s&vid=%s" % (video._id, vid),
        'title': video._n,
        'duration': int(video._dn),
        'description': video.desc,
    })

    return item


def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf8"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text=data)

if __name__ == "__main__":
    # for cid in range(0, 200):
    #     for album in CategoryCrawler().get_albums(cid):
    #         print cid
    #         break
    # CategoryCrawler(data={"cid": 6, "source": "iqiyi"}).crawl()
    # VCrawler().crawl()
    # zongyi562261, tv494534, movie578085
    AlbumCrawler(key="221001300", data={"source": "iqiyi"}).crawl()
    # AlbumCrawler.extract_key(url = "http://www.iqiyi.com/v_19rrha0szc.html")
