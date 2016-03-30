# coding=utf8
import requests
import re
import urlparse
import HTMLParser
import time
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoSourceModel, VideoItemModel

CHANNELS = {
    # 1: u"娱乐",
    # 3: u"乐活",
    # 5: u"搞笑",
    9: u"动漫",
    # 10: u"游戏",
    # 14: u"音乐",
    # 15: u"体育",
    # 21: u"科技",
    22: u"电影",
    # 25: u"成长",
    # 26: u"汽车",
    # 28: u"纪录片",
    30: u"电视剧",
    31: u"综艺",
    # 32: u"风尚",
    # 99: u"原创"
}

SERVER = "http://api.3g.tudou.com"

PARAMS_PROTOTYPE = {
    '_s_': '3a52599078ed753facd3d11891cd8670',
    #     '_t_': int(time.time()),
    'guid': '7066707c5bdc38af1621eaf94a6fe779',
    'idfa': '828C525B-ADF0-45EC-8F2C-10E5C4E1AD03',
    'network': 'WIFI',
    'ob': 'addTimeLong',
    'operator': u'中国移动_46000',
    'ouid': '19b820dc81dcfb4463380b205d20e1b80feb5d0e',
    'pid': 'c0637223f8b69b02',
    'vdid': '58434545-3CDC-4F53-956E-6C5B5E243A70',
    'ver': '3.6'
}


class ListCrawler(Crawler):
    type = "video.tudou.list"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        for cid in CHANNELS.keys():
            Scheduler.schedule(ListCrawler.type, key=str(cid), priority=conf.get(
                'priority', Priority.High), interval=conf.get('interval', 3600))

    def crawl(self):
        cid = self.key
        page = 1
        pagesize = 30

        while True:
            list_data = api_list(cid, page, pagesize)
            # 数据不为空，取出数据，page+=1
            if list_data.get('results'):
                for item in list_data.get('results'):
                    # m = re.match("^\d+$", item['tid'])
                    # if m:
                    source_id = item['tid']
                    reset = int(item['completed']) == 0

                    Scheduler.schedule(
                        type=AlbumCrawler.type,
                        key=str(source_id),
                        reset=reset
                    )
                page += 1
            # 数据为空跳出循环
            if not list_data.get('results'):
                if page > 100:
                    return
                else:
                    page += 1


class AlbumCrawler(Crawler):

    type = "video.tudou.album"

    '''
    extract_key
    '''
    @staticmethod
    def extract_key(url):
        for regex in ["http://www.tudou.com/albumplay/.+/.+\.html", "http://www.tudou.com/albumcover/.+\.html"]:
            prog = re.compile(regex)
            if re.match(prog, url):
                hxs = load_html(url)
                for s in hxs.select("/html/body/script"):
                    try:
                        text = s.select("text()").extract()[0]
                        album_id = re.findall(
                            "aid\s*[:=]\s*'{0,1}(\d+)'{0,1}", text)[0]
                        return album_id
                    except:
                        pass

    def crawl(self):
        album_id = self.key
        detail_data = api_detail(album_id)
        detail_data = detail_data.get('detail')

        channel = detail_data.get('cats')
        title = detail_data.get('title')
        title = "".join(title.split())
        image = detail_data.get('img')
        url = detail_data.get('play_url')
        url_key = re.findall(
            "http://www.tudou.com/albumplay/(.+)/.+\.html", url)[0]
        album_url = "http://www.tudou.com/albumcover/%s.html" % url_key
        if channel == u"动漫":
            actors = detail_data.get('seiyuu')
        else:
            actors = detail_data.get('performer')
        if channel == u"综艺":
            directors = detail_data.get('host')
        else:
            directors = detail_data.get('director')
        categories = detail_data.get('genre')
        region = detail_data.get('area')[0]
        description = detail_data.get('desc')
        description = "".join(description.split())
        pubtime = detail_data.get('showdate')
        # 未知发布时间pubtime != 0
        if pubtime:
            pubtime = datetime.strptime(str(pubtime), "%Y")
        # 未知发布时间pubtime == 0
        if not pubtime:
            pubtime = datetime.utcfromtimestamp(0)

        videos = get_videos(album_id, url_key)

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


def get_videos(album_id, url_key):
    list_videos = api_video(album_id)
    list_videos = list_videos.get('items')

    videos = []
    for item in list_videos:
        video = VideoItemModel({
            "title": item['title'],
            "url": "http://www.tudou.com/albumplay/%s/%s.html" % (url_key, item['itemCode']),
            "image": item['item_img_hd'],
            "duration": int(item['duration']),
            "stream": [{
                "url": "javascript:getUrl('tudou', '%s')" % item['vcode']
            }]
        })
        videos.append(video)
    return videos


def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "gbk"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text=data)


def call_api(path, params={}):
    url = urlparse.urljoin(SERVER, path)
    resp = requests.get(url, params=params)
    return resp.json()


def api_list(cid, pg, pz):
    params = PARAMS_PROTOTYPE.copy()
    params['cid'] = cid
    params['pg'] = pg
    params['pz'] = pz
    return call_api("/v3_1/channel/videos", params)


def api_detail(album_id):
    params = PARAMS_PROTOTYPE.copy()
    params['albumid'] = album_id
    return call_api("/todou/play/detail/desc", params)


def api_video(album_id):
    params = PARAMS_PROTOTYPE.copy()
    params['albumid'] = album_id
    return call_api("/v3_3/album/videos", params)


if __name__ == "__main__":
    # ListCrawler(key = 9).crawl()
    data = {
        "source": "tudou"
    }
    AlbumCrawler(key="125056", data=data).crawl()
    # AlbumCrawler.extract_key(url = "http://www.tudou.com/albumplay/55MBulduzgc/4cUPX3LrvmU.html")
