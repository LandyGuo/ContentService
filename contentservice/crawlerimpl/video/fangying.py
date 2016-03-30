#coding=utf8
import requests, re, urllib
from lxml import etree
from datetime import datetime
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoSourceModel, VideoItemModel
from contentservice.utils import get_exception_info

TOKEN = "23c566ab12d9cbfec9073dedc4d0f5ae"
PATH_HISTORY = "http://www.fangying.tv/api/history.xml"
PATH_RECOMMEND = "http://www.fangying.tv/api/recommend.xml"

CHANNELS = {
            "movie" : u"电影",
            "episode" : u"电视剧",
            "variety" : u"综艺"
            }
SITES = ["thunder"]

class HistoryCrawler(Crawler):

    type = "video.fangying.history"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        for channel in CHANNELS.iterkeys():
            Scheduler.schedule(HistoryCrawler.type, key = channel, data = {"year" : 1900}, priority = conf.get('priority', Priority.Normal), interval = conf.get('interval',86400))

    def crawl(self):
        channel = self.key
        for year in range(self.data["year"], datetime.utcnow().year + 1):
            for site in SITES:
                try:
                    items = api_history(year, channel, site)
                except:
                    self.logger.warning(get_exception_info())
                    continue

                for item in items:
                    try:
                        self.process_album(item)
                    except:
                        self.logger.warning(get_exception_info())

        self.data["year"] = datetime.utcnow().year

    def process_album(self, item):
        sites = {}
        fangying_id = re.findall("f_(.+)\.html", item['link'])[0]

        for play in item['plays']:
            site = play['site']
            if site not in SITES:
                continue

            if play["url"].find("fangying.com") != -1:
                stream = []
            else:
                format = "thunder" if site == "thunder" else ""
                stream = [{"url" : play["url"], "format" : format}]

            video = VideoItemModel({
                                    "title" : play["title"],
                                    "url" : play["url"],
                                    "stream" : stream,
                                    })

            if not sites.has_key(site):
                sites[site] = []
            sites[site].append(dict(video))

        model = None
        for site, videos in sites.iteritems():
            model = VideoSourceModel({
                        "source" : self.data['source'],
                        "source_id" : fangying_id,
                        "videos" : videos,
                        "title" : item['title'],
                        "directors" : item['directors'].split("/"),
                        "actors" : item['performers'].split("/"),
                        "description" : item['description'],
                        'categories' : item['genres'].split("/"),
                        'region' : item['countries'].split("/")[0],
                        'duration' : parse_duration(item['duration']),
                        'image' : item['avatar_middle'],
                        'score' : float(item['douban_rating']) if item.get('douban_rating') else None,
                        'url' : item['link'],
                        'price' : 0.0,
                        'pubtime' : parse_pubtime(item['release_time']),
                        'channel' : CHANNELS.get(self.key)
                 })
            export(model)

        if model:
            Scheduler.schedule(RelationCrawler.type, key = fangying_id, data = {'title' : model['title'], 'url' : model['url']})

class RelationCrawler(Crawler):
    type = "video.fangying.relation"

    def crawl(self):
        url = self.data['url']
        title = self.data['title']
        items = api_recommend(url, 10)
        related = [item['title'] for item in items]
        album = VideoSourceModel({
                         'source' : self.data['source'],
                         'title' : title,
                         'related' : related,
                         })
        export(album)

def parse_duration(text):
    m = re.match(u"(\d+)分钟", text)
    if not m:
        return None
    return int(m.group(1))

def parse_pubtime(text):
    dates = re.findall("\d\d\d\d-\d\d-\d\d", text)
    if not dates:
        return None
    dt = dates[0]
    try:
        #2013-05-00
        return datetime.strptime(dt.replace("-00", "-01"), "%Y-%m-%d")
    except:
        return None

def api_history(annum, subtype, site):
    items = []
    page = 1
    while True:
        params = {
                  "token" : TOKEN,
                  "annum" : annum,
                  "subtype" : subtype,
                  "site" : site,
                  "page" : page
                  }
        resp = requests.get(PATH_HISTORY, params = params)
        root = etree.fromstring(resp.text.encode(resp.encoding))
        page_items = [film2dct(node) for node in root.findall('film_sets/film')]
        if not page_items:
            break
        items.extend(page_items)
        total = int(root.findtext('total_page'))
        if page >= total:
            break
        page += 1
    return items

def api_recommend(url, limit):
    params = {
              'token' : TOKEN,
              'link' : url,
              'limit' : limit,
              }
    resp = requests.get(PATH_RECOMMEND, params = params)
    root = etree.fromstring(resp.text.encode(resp.encoding))
    items = [film2dct(node) for node in root.findall('film_sets/film')]
    return items

def film2dct(node):
    dct = node2dct(node)
    playnode = node.find('plays')
    if playnode is not None:
        dct['plays'] = node2list(playnode, 'play')
    return dct

def node2dct(node):
    dct = {}
    for child in node.getchildren():
        value = child.text
        dct[child.tag] = value
    return dct

def node2list(node, name):
    items = []
    for child in node.findall(name):
        items.append(node2dct(child))
    return items

def parse_bdyy(fangying_url):
    resp = urllib.urlopen(fangying_url)
    url = resp.url
    data = resp.read()
    file_url = data #Parse
    urllib.unquote(file_url)

    def repl(m):
        return unichr(int('0x' + m.group(1), 16))
    file_url = re.sub('%u([0-9A-F]{4})', file_url, repl)
    #bdhd://189815330|081655EAC30686ED9B431F0BEC2CE23B|霓虹灯下的哨兵1.rmvb


def dump_data():
    from pymongo import MongoClient
    conn = MongoClient("127.0.0.1")
    db = conn.fangying
    db.video.ensure_index([('annum', 1), ('subtype', 1), ('site', 1), ('page', 1)], unique = True)

    path = "http://www.fangying.tv/api/history.xml"

    for annum in range(1900, 2014):
        for subtype in ["movie", "episode", "variety"]:
            for site in ["bdyy", "qvod", "thunder"]:
                try:
                    page = 1
                    while True:
                        data = {
                                "annum" : annum,
                                "subtype" : subtype,
                                "site" : site,
                                "page" : page,
                                }
                        print data
                        if not db.video.find_one(data):
                            params = {
                                      "token" : "23c566ab12d9cbfec9073dedc4d0f5ae",
                                      "annum" : annum,
                                      "subtype" : subtype,
                                      "site" : site,
                                      "page" : page,
                                      }

                            resp = requests.get(path, params = params)
                            total = re.findall("<total_page>(\d+)</total_page>", resp.text)[0]
                            if page > int(total):
                                break
                            data['data'] = resp.text
                            db.video.insert(data)
                        page += 1
                except Exception, e:
                    print e


if __name__ == "__main__":
    HistoryCrawler(key = "movie", data = {"year" : 2013}).crawl()
    RelationCrawler(data = {'title' : '疯狂原始人', 'url' : 'http://www.fangying.tv/films/feng-kuang-yuan-shi-ren'}).crawl()

