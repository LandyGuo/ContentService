# -*- coding: utf8 -*-
'''
Created on Nov 30, 2013

@author: lxwu
'''
import urllib
import requests
import urlparse
from datetime import datetime
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoSourceModel, VideoItemModel

'''
http://m.56.com/api/api.ipad.php?type=3&id=51&start=0&num=16&order=times&key=09401fded433c34709fd1f1872728162&time=today
'''
SERVER = "http://m.56.com"
key = "09401fded433c34709fd1f1872728162"

client_info = {
    "model": "iPad",
    "os": "ios",
    "screen": "1024x768",
    "from": 9100701,
    "version": "1.1.3",
    "uniqid": "a70c3e422522639052af9d0234d8df5797464e06",
    "product": "56video_pad",
    "mac": "02:00:00:00:00:00",
    "net_type": "wifi",
    "os_info": "iPhone OS7.0.4",
    "op": "op"
}

CHANNELS = {
    51: u"电影",
    52: u"电视剧",
    53: u"原创",
    54: u"综艺",
    55: u"娱乐",
    56: u"资讯",
    57: u"搞笑",
    107: u"音乐"
}

LONG_VIDEO_CHANNELS = {
    51: u"电影",
    52: u"电视剧",
    54: u"综艺",
}


class ListCrawler(Crawler):

    type = "video.video56.list"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        for id, channel in CHANNELS.iteritems():
            data = {
                "channel": channel
            }
            Scheduler.schedule(
                ListCrawler.type,
                key=id,
                data=data,
                priority=conf.get('priority', Priority.High),
                interval=conf.get('interval', 3600)
            )

    def crawl(self):
        type = 3
        channel_id = self.key
        channel = self.data['channel']
        start = 0
        num = 16
        params = {
            "order": "times",
            "time": "today"
        }

        while 1:
            list_data = api_list(type, channel_id, start, num, params)
            if start == list_data['num']:
                return
            for item in list_data['data']:
                if channel in LONG_VIDEO_CHANNELS.values():
                    source_id = item['mid']
                    tags = []
                    time = item['public_time']
                    time = datetime.strptime(time, "%Y%m%d")

                    lastdata = Scheduler.get_data(AlbumCrawler.type, source_id)
                    lasttime = lastdata.get(
                        "time", datetime.min) if lastdata else datetime.min
                    reset = time > lasttime
                else:
                    source_id = item['flvid']
                    tags = item.get("tags").split(",")
                    time = datetime.utcnow()
                    reset = False

                data = {
                    "url": item.get("web_url"),
                    "title": item.get("title"),
                    "image": item.get("bpic"),
                    "image2": item.get("mpic"),
                    "description": item.get("introduce"),
                    "duration": item.get("duration"),
                    "tags": tags,
                    "time": time,
                    "channel": channel
                }

                Scheduler.schedule(
                    AlbumCrawler.type,
                    source_id,
                    data,
                    reset=reset
                )
            start += 1


class AlbumCrawler(Crawler):

    type = "video.video56.album"

    @staticmethod
    def extract_key(url):
        pass

    def crawl(self):
        type = 4
        album_id = self.key
        title = self.data['title'].encode('utf-8')
        channel = self.data.get('channel')

        if channel in LONG_VIDEO_CHANNELS.items():
            album_data = api_album(type, album_id, title)
            album_data = album_data['data']
            pubtime = album_data.get("public_time")
            pubtime = datetime.strptime(pubtime, "%Y%m%d")

            videos = []
            for video in album_data['data']:
                video = clean_video(video)
                videos.append(video)

            model = VideoSourceModel({
                "source": self.data.get('source'),
                "source_id": album_id,
                "title": title,
                "image": album_data.get("bpic"),
                "image2": album_data.get("mpic"),
                "url": album_data.get("web_url"),
                "actors": album_data.get("actors"),
                "directors": album_data.get("director"),
                "categories": album_data.get("tname"),
                "tags": self.data.get("tags"),
                "channel": channel,
                "region": album_data.get("zname")[0],
                "description": album_data.get("introduce"),
                "pubtime": pubtime,
                "videos": videos,
            })
        else:
            video = VideoItemModel({
                                   "title": title,
                                   "description": self.data.get("description"),
                                   "url": "http://www.56.com/u13/v_%s.html" % album_id,
                                   "stream": [{"url": "http://vxml.56.com/html5/%s/?src=3g&res=qqvga" % album_id}],
                                   "stream_high": [{"url": "http://vxml.56.com/html5/%s/?src=3g&res=qvga" % album_id}]
                                   })
            model = VideoSourceModel({
                "source": self.data.get('source'),
                "source_id": album_id,
                "title": title,
                "image": self.data.get("bpic"),
                "image2": self.data.get("mpic"),
                "tags": self.data.get("tags"),
                "url": self.data.get("web_url"),
                "channel": channel,
                "description": self.data.get("introduce"),
                "videos": [video],
            })
        export(model)
        self.data['to_album_id'] = model['to_album_id']


def clean_video(video):
    video = video['video']
    flvid = video.get('flvid')
    duration = video.get('duration')
    duration = map(int, duration.split(":"))
    if len(duration) == 2:
        duration = duration[0] * 60 + duration[1]
    elif len(duration) == 3:
        duration = duration[0] * 3600 + duration[1] * 60 + duration[2]
    video = VideoItemModel({
                           "title": video.get('title'),
                           "image": video.get('img'),
                           "duration": duration,
                           "description": video.get('introduce'),
                           "url": "http://www.56.com/u13/v_%s.html" % flvid,
                           "stream": ["http://vxml.56.com/html5/%s/?src=3g&res=qqvga" % flvid],
                           "stream_high": ["http://vxml.56.com/html5/%s/?src=3g&res=qvga" % flvid]
                           })
    return video


def call_api(path, params={}):
    params["key"] = key
    params["client_info"] = urllib.quote(str(client_info))
    url = urlparse.urljoin(SERVER, path)
    resp = requests.get(url, params=params)
    return resp.json()


def api_list(type, channel_id, start, num, params):
    params["type"] = type
    params["id"] = channel_id
    params["start"] = start
    params["num"] = num
    return call_api("/api/api.ipad.php", params)


def api_album(type, album_id, title):
    params = {
        "type": type,
        "mid": album_id,
        "title": urllib.quote(title)
    }
    return call_api("/api/api.ipad.php", params)

if __name__ == "__main__":
    # for k, v in CHANNELS.iteritems():
    #     data = {
    #             "channel": v
    #             }
    #     ListCrawler(key=k, data=data).crawl()
    ListCrawler(key=57, data={"channel": u"搞笑", "source": "video56"}).crawl()
    # data = {
    #         "source": "video56",
    #         "title": u"咱们结婚吧",
    #         "channel": u"电视剧"
    #         }
    # AlbumCrawler(key="6175", data=data).crawl()
