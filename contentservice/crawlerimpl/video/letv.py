# coding=utf8
from django.conf import settings
import requests
import re
import urlparse
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, export, Priority, Scheduler
from contentservice.models.video import VideoItemModel,  VideoSourceModel, VideoRankModel

SERVER = "http://static.app.m.letv.com"
pcode = "010210000"
version = "5.0"


class ListCrawler(Crawler):
    type = "video.letv.list"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        data = api_channel(pcode, version)
        for channel in data['body']['channel']:
            cid = channel.get("cid")
            channel_name = channel.get("name")
            crawl_data = {
                "channel_id": cid,
                "channel_name": channel_name,
            }
            Scheduler.schedule(ListCrawler.type, key=cid, data=crawl_data, priority=conf.get(
                'priority', Priority.High), interval=conf.get('interval', 3600))

    def crawl(self):
        cid = self.key
        channel = self.data.get("channel_name")
        itemid = 0
        date = 0
        areaid = 0
        sort = 2  # 1:最新 2:最热
        start = 0
        num = 30

        while True:
            list_data = api_list(
                cid, itemid, date, areaid, sort, start, num, pcode, version)
            list_data = list_data.get("body")

            if list_data.get("data"):
                for item in list_data['data']:
                    source_id = item.get("id")
                    image = item.get("icon")
                    reset = int(item['isend']) == 0

                    Scheduler.schedule(
                        type=AlbumCrawler.type,
                        key=source_id,
                        data={
                            "channel": channel,
                            "image": image
                        },
                        reset=reset
                    )

                start += 1

            if not list_data.get("data"):
                return


class AlbumCrawler(Crawler):
    type = "video.letv.album"

    '''
    http://so.letv.com/tv/92520.html
    '''
    @staticmethod
    def extract_key(url):
        for regex in ["^http://so.letv.com/[a-z]+/(\d+)\.html$"]:
            key = re.findall(regex, url)
            if key != []:
                return key[0]

    def crawl(self):
        source_id = self.key
        album_data = api_album(source_id, pcode, version)
        album_data = album_data['body']
        title = album_data.get("nameCn")
        pubtime = album_data.get("releaseDate")
        if re.match("^\d+$", pubtime):
            pubtime = datetime.strptime(pubtime, "%Y")
        elif re.match("^\d+-\d+-\d+$", pubtime):
            pubtime = datetime.strptime(pubtime, "%Y-%m-%d")
        else:
            pubtime = datetime.utcfromtimestamp(0)
        directors = album_data.get("directory").split(" ")
        actors = album_data.get("starring").split(" ")
        desc = album_data.get("description")
        desc = "".join(desc.split())
        region = album_data.get("area")
        categories = album_data.get("subCategory").split(" ")
        tags = album_data.get("tag").split(" ")
        url = "http://so.letv.com/tv/%s.html" % source_id

        videos = []
        b = 1
        s = 60
        o = -1
        m = 0
        series_data = api_series(source_id, b, s, o, m, pcode, version)
        for series in series_data['body']['videoInfo']:
            id = series['id']
            mid = series['mid']
            url = "http://www.letv.com/ptv/vplay/%s.html" % id
            vurl = "http://dynamic.app.m.letv.com/android/dynamic.php?mod=minfo&ctl=videofile&act=index&mmsid=%s&pcode=%s&version=%s" % (
                mid, pcode, version)
            jsurl = "javascript:getUrl('letv', '%s')" % vurl
            video = VideoItemModel({
                "title": series.get("nameCn"),
                "url": url,
                "stream": [{
                    "url": jsurl
                }],
                "image": series.get("picAll"),
                "duration": series.get("duration")
            })
            videos.append(video)

        model = VideoSourceModel({
                                 "source_id": source_id,
                                 "source": self.data.get('source'),
                                 "url": url,
                                 "channel": self.data['channel'],
                                 'title': title,
                                 "image": self.data['image'],
                                 "pubtime": pubtime,
                                 "directors": directors,
                                 "actors": actors,
                                 "desc": desc,
                                 "region": region,
                                 "categories": categories,
                                 "tags": tags,
                                 "videos": videos
                                 })
        export(model)
        self.data['to_album_id'] = model['to_album_id']


def call_api(path, headers=None):
    if not headers:
        headers = {}
    headers.update(settings.DEFAULT_HEADERS)
    url = urlparse.urljoin(SERVER, path)
    resp = requests.get(url)
    return resp.json()


def api_channel(pcode, version):
    url = "/android/mod/mob/ctl/channelinfo/act/index/pcode/%s/version/%s.mindex.html" % (
        pcode, version)
    return call_api(url)


def api_list(cid, itemid, data, areaid, sort, start, num, pcode, version):
    url = "/android/mod/minfo/ctl/list/act/index/cid/%s/itemid/%s/date/%s/areaid/%s/orderby/playcount/sort/%s/start/%s/num/%s/pcode/%s/version/%s.mindex.html" % (
        cid, itemid, data, areaid, sort, start, num, pcode, version)
    return call_api(url)


def api_album(source_id, pcode, version):
    url = "/android/mod/mob/ctl/album/act/detail/id/%s/pcode/%s/version/%s.mindex.html" % (
        source_id, pcode, version)
    return call_api(url)


def api_series(source_id, b, s, o, m, pcode, version):
    url = "http://static.app.m.letv.com/android/mod/mob/ctl/videolist/act/detail/id/%s/b/%s/s/%s/o/%s/m/%s/pcode/%s/version/%s.mindex.html" % (
        source_id, b, s, o, m, pcode, version)
    return call_api(url)


def load_html(url, headers=None):
    if not headers:
        headers = {}
    headers.update(settings.DEFAULT_HEADERS)
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf8"
    return HtmlXPathSelector(text=resp.text)

if __name__ == "__main__":
    # data = {
    #     "channel_id": 5,
    #     "channel_name": "电视剧",
    # }
    # ListCrawler(key=5, data=data).crawl()
    data = {
        "source": "letv",
        "image": "http://i3.letvimg.com/vrs/201312/24/3f3a825a5d134e06a011024f8343507d.jpg",
        "channel": u"电视剧"
    }
    AlbumCrawler(key="95180", data=data).crawl()
    # AlbumCrawler.extract_key(url = "http://www.tudou.com/albumplay/55MBulduzgc/4cUPX3LrvmU.html")
