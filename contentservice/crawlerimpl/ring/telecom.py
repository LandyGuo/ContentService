#coding=utf8
'''
http://open.189.cn/index.php?m=ability&c=index&a=ability_index

access_token=8d146f150d65b5a0914e289096e631c71367572641174&expires_in=1019532&open_id=133649617832960100
app_id=367832960000031047&app_secret=62a5af901b9deaad644ef0434aa9bb5e
'''
import requests
from datetime import datetime, timedelta
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, export, Priority, Scheduler
from contentservice.models.ring import RingBackModel, RingToneModel, RingToneRankModel

SOURCE = "ct"

APP_ID = "163648310000031414"
APP_SECRET = "290d5398447b1af8cc23e7b88590b4a0"
ACCESS_TOKEN = 'e243888940ec71503bf380b95958d8581370664738247'
ACCESS_TOKEN_EXPIRES = datetime.max
HOST = "http://api.189.cn"

class BillboardCrawler(Crawler):

    type = "ring.telecom.billboard"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(BillboardCrawler.type, key = "", priority = Priority.High, interval = 3600)

    def crawl(self):
        for item in get_billboard_list():
            data = {
                    "name" : item['billboardName'],
                    "id" : item['billboardID'],
                    }
            try:
                self.crawl_billboard(data)
            except:
                pass

    def crawl_billboard(self, billboard):
        ringbacks = []
        songs = get_billboard(billboard["id"])
        for song in songs:
            ringback = RingBackModel({"title" : song["name"], "artist" : song["actorName"]})
            ringbacks.append(ringback["key"])
            data = {
                    "id" : song["id"],
                    "title" : song["name"],
                    "artist": song["actorName"],
                    }
            Scheduler.schedule(SongCrawler.type, key = "rank_%s" % song["id"], data = data, priority = Priority.High)


class SongCrawler(Crawler):

    type = "ring.telecom.song"

    def crawl(self):

        lyrics = "" #get_lyrics(self.data['id'])   API has no data so far
        tracks = get_tracks(self.data['id'])

        if tracks:
            track = tracks[0]
            ringtone_preview = get_ringtone_preview(track['resID'])
            if ringtone_preview:
                ringtone = RingToneModel({
                                  "source" : SOURCE,
                                  "source_id" : self.data["id"],
                                  "title" : self.data["title"],
                                  "artist" : self.data["artist"],
                                  "album" : self.data.get("album"),
                                  "language" : self.data.get("language"),
                                  "time" : self.data.get("time"),
                                  "image" : self.data.get("image"),
                                  "description" : self.data.get("description"),
                                  "lyrics" : lyrics,
                                  "url" : ringtone_preview.get("fileAddress"),
                                  "duration" : ringtone_preview.get("playTime", 0) / 1000,
                                  })
                export(ringtone)

            info = get_crbtinfo(track['resID'] )
            if info:
                expires = info.get("invalidTime")
                if expires:
                    expires = datetime.strptime(expires[:10], "%Y-%m-%d") + timedelta(hours = 8)

                ringback_preview = get_ringback_preview(track['resID'])
                if not ringback_preview:
                    ringback_preview = ringtone_preview

                if ringback_preview:
                    ringback = RingBackModel({
                                  "source" : SOURCE,
                                  "source_id" : self.data["id"],
                                  "title" : self.data["title"],
                                  "artist" : self.data["artist"],
                                  "album" : self.data.get("album"),
                                  "language" : self.data.get("language"),
                                  "time" : self.data.get('time'),
                                  "image" : self.data.get("image"),
                                  "description" : self.data.get("description"),
                                  "lyrics" : lyrics,

                                  "url" : ringback_preview.get("fileAddress"),
                                  "duration" : ringback_preview.get("playTime", 0) / 1000,

                                  "price" : info.get("price", 0) / 100.0,
                                  "purchase" : info.get("mdmcId"),
                                  "expires" : expires,
                                  })
                    export(ringback)



class ArtistListCrawler(Crawler):

    type = "ring.telecom.artistlist"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(type = ArtistListCrawler.type, key = "", priority = Priority.High, interval = 86400 * 7)

    def crawl(self):
        cate_ids = get_artist_categories()
        for cate_id in cate_ids:
            for artist in get_artists(cate_id):
                Scheduler.schedule(type = ArtistCrawler.type, key = artist["id"], priority = Priority.Low)

class ArtistCrawler(Crawler):

    type = "ring.telecom.artist"

    def crawl(self):
        artist_id = self.key

        for album in get_albums(artist_id):
            for song in get_songs_by_album(album['id']):
                self.extract_song(song)

        for song in get_songs_by_artist(artist_id):
            self.extract_song(song)

    def extract_song(self, song, album = None):
        try:
            pubtime = song.get("publishTime")
            data = {
                    "artist" : song["actorName"],
                    "title" : song["name"],
                    "id" : song["id"],
                    "time" : datetime.strptime(pubtime[:10], "%Y-%m-%d") if pubtime else None,
                    "language" : album.get("language") if album else None,
                    "album" : album.get("name") if album else None,
                    "description" : album.get("intro") if album else None,
                    "image" : album.get("url") if album else None,
                    }
        except:
            self.logger.warning("parse song error: %s" % song)
            return
        key = str(song['id']) if album else str(song['id']) + "_noalbum"
        Scheduler.schedule(type = SongCrawler.type, key = key, data = data)


class ArtistIDCrawler(Crawler):

    type = "ring.telecom.artistid"

    @staticmethod
    def init(conf=None):
        group_size = 1000
        for artist_id in xrange(0, 440000, group_size):
            data = {"start_id" : artist_id, "end_id" : artist_id + group_size}
            Scheduler.schedule(ArtistIDCrawler.type, key = str(artist_id / group_size), data = data, priority = Priority.High)

    def crawl(self):
        for artist_id in xrange(self.data['start_id'], self.data['end_id']):
            try:
                info = get_artist_info(artist_id)
                if info:
                    self.logger.info("artist_id - %s" % artist_id)
                    Scheduler.schedule(ArtistCrawler.type, key = str(artist_id))
            except:
                pass


'''
http://www.118100.cn/
'''
IMUSIC_HOST = "http://www.118100.cn"
class IMusicRankCrawler(Crawler):
    type = 'ring.telecom.imusicrank'

    @staticmethod
    def init(conf=None):
        key = 'jd-461847-9'
        data = {
                    'type' : 'new',
                    'title' : u'飙升',
                    'ringback' : [],
                    'ringtone' : True
                }
        Scheduler.schedule(IMusicRankCrawler.type, key = key, data = data, priority = Priority.High, interval = 86400)

    def crawl(self):
        page = 1
        keys = []
        while True:
            url = IMUSIC_HOST + "/v6/billboard/list/%s-%s.html" % (self.key, page)
            text = requests.get(url).text
            hxs = HtmlXPathSelector(text = text)
            for s in hxs.select("//div[@class='list-box1']/ul/li[@class='row']"):
                try:
                    title = s.select("span[@class='l3']/a/text()").extract()[0]
                    artist = s.select("span[@class='l4']/a/text()").extract()[0]
                    key = RingBackModel({'title' : title, 'artist' : artist})['key']
                    keys.append(key)
                except:
                    pass

            page += 1
            if not hxs.select("//a[contains(@href,'%s-%s.html')]" % (self.key, page)).extract():
                break

        if self.data['ringtone']:
            export(RingToneRankModel({
                    "source" : SOURCE,
                    "type" : self.data["type"],
                    "title" : self.data['title'],
                    "ringtones" : keys,
                    }))


def get_access_token():
    global ACCESS_TOKEN, ACCESS_TOKEN_EXPIRES

    if (not ACCESS_TOKEN) or (ACCESS_TOKEN_EXPIRES <= datetime.utcnow()):
        params = {
                  "grant_type" : "client_credentials",
                  "app_secret" : APP_SECRET,
                  "app_id" : APP_ID,
                  }
        data = requests.post("http://oauth.api.189.cn/emp/oauth2/v2/access_token", params).json()
        token =  data['access_token']

        ACCESS_TOKEN = token
        ACCESS_TOKEN_EXPIRES = datetime.utcnow() + timedelta(days = 1)

    return ACCESS_TOKEN

def call_api(path, params = {}):
    url = HOST
    if not path.startswith("/"):
        url += "/"
    url += path
    headers = {
               'app_id' : APP_ID,
               'access_token' : get_access_token(),
               }
    data = requests.get(url, params = params, headers = headers).json()
    return data


def get_billboard_list():
    path = "/imusic/content/contentBillboardservice/queryBillboardListInfo"
    data = call_api(path)
    return data['QueryBillboardListJTResponse']['billboardList']['billboard']

#actorName (4559596928)    unicode: 萧亚轩
#id (4559601856)    int: 2522697
#name (4559596112)    unicode: 潇洒小姐
def get_billboard(billboard_id):
    index = 0
    limit = 100
    songs = []
    while True:
        params = {
                  "billboardType" : billboard_id,
                  "startNum" : index,
                  "maxNum" : limit,
                  }
        data = call_api("/imusic/content/contentBillboardservice/queryContentBillboardInfo", params)
        try:
            items = data['QueryContentBillboardJTResponse']['musicItemList']['musicItem']
            if isinstance(items, list):
                songs.extend(items)
            else:
                break
        except:
            break
        index += limit

    return songs

#aiYueDian (4366898016)    int: 1
#bizType (4365619296)    int: 4
#contentId (4365614752)    int: 2703747
#invalidTime (4365614368)    unicode: 2013-09-30T00:00:00+08:00
#mdmcId (4363274016)    int: 167000006900
#mdmcMusicId (4365619392)    int: 1670000069
#memberType (4365613552)    int: 0
#price (4365619488)    int: 100
def get_trackinfo(res_id):
    params = {
              "mdmcMusicId" : res_id
              }
    data = call_api("/imusic/product/productquery/queryfullTrackinfo", params)
    info = data.get("MusicProductInfoJTResponse")
    if isinstance(info, dict):
        return info
    return None

#bitRate (4433248928)    int: 16
#chord (4433225072)    int: 40
#contentID (4433248976)    int: 2522697
#fileAddress (4433248784)    unicode: http://118.85.203.45/res/thirdparty/1080/mp3/00/26/47/1080002647010400.mp3?deviceid=null&qd=null
#filesize (4431941728)    int: 446464
#format (4431937280)    unicode: mp3
#playTime (4433249840)    int: 219168
#resID (4433248880)    int: 1080002647
def get_tracks(content_id):
    params = {
              "id" : content_id,
              "idtype" : 5,
        #      "format" : "mp3",
              }
    data = call_api("/imusic/audio/iaudiomanager/queryfulltrackbyid", params)

    try:
        tracks = data["AudioFileJTResponse"]['audioFileItemList']['audioFileItem']
        if isinstance(tracks, list):
            return tracks
    except:
        pass
    return None


def get_songinfo(id, type = 5):
    params = {"id" : id, "type" : type}
    data = call_api("/music/openapi/services/product/productquery/querySongInfo", params)
    return data

def get_crbtinfo(music_id):
    params = {
                'mdmcMusicId' : music_id,
            }
    data = call_api("/imusic/product/productquery/querycrbtinfo", params)
    return data['MusicProductInfoJTResponse']

def get_lyrics(content_id):
    params = {
              "contentID" : content_id,
              "type" : ""
              }
    data = call_api("/imusic/lyric/lyric/querylyricbycontentid", params)
    try:
        lyrics = data["queryLyricJTResponse"]["lyric"]["text"]
        return lyrics
    except:
        pass
    return None

def get_artist_categories():
    params = {
              "startNum" : 0,
              "maxNum" : 100,
              "order" : "",
              }
    data = call_api("/imusic/cate/catemanager/querycatelist", params)

    cate_ids = []
    for item in data['items']:
        if item.get('id') == "Artist":
            for cate in item['childrenCateItem']:
                cate_ids.append(cate['id'])
    return cate_ids

def get_artist_info(artist_id):
    params = {
                'id' : artist_id,
                'idtype' : 0,
              }
    data = call_api("/imusic/actorAblum/actoralbum/getactorinfo", params)
    resp = data['QueryActorJTResponse']
    return resp["item"] if resp.get('res_code') == 0 else None

def get_artists(cate_id):
    index = 0
    limit = 100
    artists = []
    while True:
        params = {
                  "cateID" : cate_id,
                  "startNum" : index,
                  "maxNum" : limit,
                  "order" : "",
                  }
        data = call_api("/imusic/cate/catemanager/queryactorsinfo", params)
        items = data["queryActorsJTResponse"].get("items")
        if not isinstance(items, list):
            break
        artists.extend(items)
        index += limit
    return artists

def get_albums(artist_id):
    index = 1
    limit = 100
    albums = []
    params = {
              "actorId" : artist_id,
              "startNum" : index,
              "maxNum" : limit,
              "order" : "",
              }
    data = call_api("/imusic/actorAblum/actoralbum/findalbumsbyactor", params)
    items = data["queryAlbumsJTResponse"].get("album")
    if isinstance(items, list):
        albums.extend(items)
    return albums

def get_songs_by_artist(artist_id):
    index = 1
    limit = 100
    songs = []
    while True:
        params = {
                  "actorID" : artist_id,
                  "startNum" : index,
                  "maxNum" : limit,
                  "order" : "",
                  }
        data = call_api("/imusic/actorAblum/actoralbum/findmusicofactor", params)
        items = data["QueryMusicsJTResponse"].get("mitems")
        if not isinstance(items, list):
            break
        songs.extend(items)
        index += 1
    return songs

def get_songs_by_album(album_id):
    index = 1
    limit = 100
    songs = []
    params = {
              "albumId" : album_id,
              "startNum" : index,
              "maxNum" : limit,
              "order" : "",
              }
    data = call_api("/imusic/actorAblum/actoralbum/findmusicsbyalbumid", params)
    items = data["QueryMusicsJTResponse"].get("mitems")
    if isinstance(items, list):
        songs.extend(items)
    return songs

def get_ringback_preview(content_id):
    params = {
              "mdmcMusicId" : content_id,
              "format" : "wma",
              }
    data = call_api("/imusic/audio/iaudiomanager/querycrbt", params)
    try:
        items = data['AudioFileJTResponse']['audioFileItemList']['audioFileItem']
        if not isinstance(items, list):
            items = []
    except:
        items = []

    for item in items:
        bit_rate = item.get('bitRate')
        if bit_rate and bit_rate >= 48 and bit_rate <= 128:
            return item
    return items[0] if items else None


def get_ringtone_preview(content_id):
    params = {
              "mdmcMusicId" : content_id,
              "format" : "",
              }
    data = call_api("/imusic/audio/iaudiomanager/queryringtone", params)
    try:
        items = data['AudioFileJTResponse']['audioFileItemList']['audioFileItem']
        if not isinstance(items, list):
            items = []
    except:
        items = []

    for item in items:
        bit_rate = item.get('bitRate')
        if bit_rate and bit_rate >= 48 and bit_rate <= 128:
            return item
    return items[0] if items else None

def get_catelist():
    def extract_items(datas):
        items = []
        if datas:
            if not isinstance(datas, list):
                datas = [datas]
            for data in datas:
                items.append({'title' : data.get('des'), 'id' : data.get('id')})
                items.extend(extract_items(data.get('childrenCateItem')))
        return items

    data = call_api("/imusic/cate/catemanager/querycatelist")
    items = extract_items(data.get('childrenCateItem'))
    return items

if __name__ == "__main__":
    data = get_crbtinfo(1670000069)
    print data

