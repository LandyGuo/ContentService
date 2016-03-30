#coding=utf8
'''
http://open.migu.cn/index.php  Jeffre@123654
'''
import urllib2, time
from lxml import etree
from datetime import datetime, timedelta
from contentservice.crawler import Crawler, export, Priority, Scheduler
from contentservice.models.ring import RingBackModel, RingToneModel

SERVER = "http://218.200.227.123:90/wapServer/1.0"

SOURCE = "cm"

API_RETRIES = 3
API_RETRY_INTERVAL = 1.0

class RankCrawler(Crawler):

    type = "ring.mobile.rank"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(RankCrawler.type, key = "", priority = Priority.High, interval = 3600)

    def crawl(self):
        ringbacks = []
        for rank in get_rank_list():
            try:
                musics = get_musics_by_rank(rank["chartCode"])
            except Exception, e:
                self.logger.warning("Get music failed - %s" % e)
                continue
            for music in musics:
                ringback = RingBackModel({
                                          "title" : music["songName"],
                                          "artist" : music["singerName"]
                                          })
                ringbacks.append(ringback["key"])
                Scheduler.schedule(MusicCrawler.type, key = music["musicId"], data = music)

                for artist_id in music['singerId'].split(","):
                    if artist_id.isdigit():
                        Scheduler.schedule(ArtistCrawler.type, key = artist_id)



class ArtistIDCrawler(Crawler):

    '''
    id range:
    0 - 1100000, 1000000000 - 1000100000
    425818, 476361
    955111, 1092949
    '''

    type = "ring.mobile.artistid"

    @staticmethod
    def init(conf=None):
        group_size = 1000
        for artist_id in xrange(1000, 150000, group_size):
            data = {"start_id" : artist_id, "end_id" : artist_id + group_size}
            Scheduler.schedule(ArtistIDCrawler.type, key = str(artist_id / group_size), data = data)

    def crawl(self):
        for artist_id in xrange(self.data['start_id'], self.data['end_id']):
            try:
                items = get_musics_by_artist(artist_id, limit = 1)
                if items:
                    self.logger.info("artist_id - %s" % artist_id)
                    Scheduler.schedule(ArtistCrawler.type, key = str(artist_id))
            except:
                pass

class ArtistCrawler(Crawler):

    type = "ring.mobile.artist"

    def crawl(self):
        artist_id = int(self.key)
        musics = get_musics_by_artist(artist_id, logger = self.logger)
        for music in musics:
            #MusicCrawler(key = music["musicId"], data = music).crawl()
            Scheduler.schedule(MusicCrawler.type, key = music["musicId"], data = music, interval = 86400 * 7)


class MusicCrawler(Crawler):

    type = "ring.mobile.music"

    def crawl(self):
        music = self.data

        url = music.get("crbtListenDir")
        if not url:
            return

        lyrics = None#get_lyrics(music['lrcDir'])

        try:
            expires = datetime.strptime(music["crbtValidity"], "%Y%m%d") + timedelta(hours = 8)
        except:
            expires = None

        ringback = RingBackModel({
                       "source" : SOURCE,
                       "source_id" : music.get("musicId"),
                       "title" : music.get("songName"),
                       "artist" : music.get("singerName"),
                       "image" : music.get("albumPicDir"),
                       "url" : url,
                       "lyrics" : lyrics,
                       "price" : float(music.get("price", 0)) / 100,
                       "expires" : expires,
                       "purchase" : music.get("musicId"),
                       })

        ringtone = RingToneModel({
                       "source" : SOURCE,
                       "source_id" : music.get("musicId"),
                       "title" : music.get("songName"),
                       "artist" : music.get("singerName"),
                       "image" : music.get("albumPicDir"),
                       "url" : url,
                       "lyrics" : lyrics,
                       })

        export(ringback)
        export(ringtone)

def get_lyrics(url):
    if not url:
        return None
    try:
        data = urllib2.urlopen(url).read()
        lyrics = unicode(data, "gbk")
    except:
        return None
    return lyrics


def call_api(path, params = {}, xmlroot = None):
    IMSI = "3202CD2CFB76C6A118C648D9A50D2B23"
    app_id = "004122103515537102"
    pub_key = "4904618A763F1A7A1D741170FB851C7B"
    net_mode = "WIFI"
    package_name = "com.lingyinbao.ring.android"
    version = "C1.0"
    excode = "null"

    auth = 'OEPAUTH realm="OEP",IMSI="%s",appID="%s",pubKey="%s",netMode="%s",packageName="%s",version="%s",excode="%s"'\
            % (IMSI, app_id, pub_key, net_mode, package_name, version, excode)

    if not path.startswith("/"):
        path = "/" + path
    url = SERVER + path

    headers = {"Authorization" : auth}

    root = dct2node(params, "request") if not xmlroot else xmlroot
    data = etree.tostring(root)

    retry_count = 0
    while True:
        try:
            req = urllib2.Request(url, data, headers)
            data = urllib2.urlopen(req).read()

            retroot = etree.fromstring(data)

            code = retroot.findtext("resCode")
            if code != "000000":
                raise Exception("Call api failed: path = %s, params = %s, retdata = %s" % (path, params, data))
            return retroot

        except Exception:
            retry_count += 1
            if retry_count >= API_RETRIES:
                raise
            time.sleep(API_RETRY_INTERVAL)


def call_list_api(path, params, item_name, limit = None, logger = None):
    items = []
    page = 1
    total = None
    page_size = 30
    while True:
        params["pageNumber"] = page
        params["numberPerPage"] = page_size
        try:
            root = call_api(path, params)
            data = node2list(root, item_name)

            if page == 1:
                total_text = root.findtext("resCounter")
                if total_text and total_text.isdigit():
                    total = int(total_text)
        except Exception, e:
            if logger:
                logger.warning(e)
            data = []

        items.extend(data)
        if total and page >= (total - 1) / page_size + 1:
            break
        if (total is None) and (not data):
            break
        if limit and len(items) >= limit:
            items = items[:limit]
            break
        page += 1
    return items

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

def dct2node(dct, name):
    node = etree.Element(name)
    for key, value in dct.iteritems():
        child = etree.Element(key)
        child.text = unicode(value)
        node.append(child)
    return node

def get_rank_list():
    items = call_list_api("/search/chart/list", {}, "ChartInfo")
    return items

def get_musics_by_rank(rank_id):
    params = {"chartCode" : rank_id}
    items = call_list_api("/search/music/listbychart", params, "MusicInfo")
    return items

def get_musics_by_artist(artist_id, limit = None, logger = None):
    params = {"singerId" : artist_id}
    items = call_list_api("/search/music/listbysinger", params, "MusicInfo", limit = limit, logger = logger)
    return items

def get_albums_by_artist(artist_id):
    params = {"singerId" : artist_id}
    items = call_list_api("/search/album/listbysinger", params, "AlbumInfo")
    return items

def get_musics_by_album(album_id):
    params = {"albumId" : album_id}
    items = call_list_api("/search/music/listbyalbum", params, "MusicInfo")
    return items

def get_artists(artist_ids):
    root = etree.Element("request")
    for artist_id in artist_ids:
        node = etree.Element("singerId")
        node.text = unicode(artist_id)
        root.append(node)
    root = call_api("/search/singer/list", xmlroot = root)
    items = node2list(root, "SingerInfo")
    return items


def get_tags(tag_id = 0):
    params = {"tagId" : tag_id}
    items = call_list_api("/search/tag/list", params, "TagInfo")
    return items

def get_audio_url(music_id):
    params = {"musicId" : music_id}
    root = call_api("/stream/query", params)
    url = root.findtext("streamUrl")
    return url

def get_ringback_preview(music_id):
    params = {"musicId" : music_id}
    root = call_api("/crbt/prelisten", params)
    return node2dct(root)

def order_ringback(music_id):
    params = {"musicId" : music_id, "validCode" : ""}
    root = call_api("/crbt/order", params)
    return node2dct(root)

def search_music(query):
    params = {'key' : query}
    items = call_list_api("/search/music/listbykey", params, "MusicInfo", limit = 30)
    return items

def get_album_by_music(music_id):
    params = {"musicId" : music_id}
    items = call_list_api("/search/album/listbymusic", params, "AlbumInfo")
    return items

if __name__ == "__main__":

    #ArtistCrawler(key = "112").crawl()


    items = search_music('再见青春')
    print items[0]
    print items[0]['songName']

    items = get_musics_by_artist(1000006307)
    for item in items:
        if item['songName'] == '江南style':
            print item

    for id in range(60000, 100000, 100):
        items =  get_albums_by_artist(id)
        print id, len(items)



#{'count': None, 'lrcDir': 'http://open.migu.cn:8100/music/3/000021/2012/12/21/3623000/3/QogQUSB1tS62i3622724.lrc?m', 'singerId': '54382', 'ringValidity': '20151231', 'singerName': u'\u9177\u5154\u5154', 'price': '200', 'musicId': '9bf7ccf7734c4bffba95f046b4f05943', 'crbtListenDir': 'http://open.migu.cn:8100/music/0/000000/2012/12/19/755001/3/K1I11O57650Z41754392.mp3?m', 'ringListenDir': 'http://open.migu.cn:8100/music/0/000000/2012/12/19/755001/3/K1I11O57650Z41754392.mp3?m', 'songValidity': '20151231', 'songListenDir': 'http://open.migu.cn:8100/music/3/000019/2012/12/21/3623000/3/epzWhEhC413n83622696.mp3?m', 'crbtValidity': '20151231', 'singerPicDir': None, 'songName': u'\u5c31\u4e0d\u63a5\u7535\u8bdd', 'albumPicDir': None}
