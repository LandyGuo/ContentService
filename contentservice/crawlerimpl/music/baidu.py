# -*- coding: utf-8 -*-
import json
from scrapy.selector import HtmlXPathSelector
from contentservice.models.music import MusicModel, MusicAlbumModel, MusicArtistModel
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.utils import downloader
from contentservice.utils.datetimeutil import parse_date

SOURCE = "baidu"

def call_rest(method, params = {}):
    params['method'] = method
    params['format'] = 'json'
    url = "http://tingapi.ting.baidu.com/v1/restserver/ting"
    resp = downloader.download(url = url, params = params)
    data = json.loads(resp.body)
    errcode = data.get('error_code')
    if errcode and (not errcode == 22000):
        raise Exception("api returns error")
    return data


class HotCrawler(Crawler):

    type = "music.baidu.hot"

    @staticmethod
    def init(conf=None):

        def generate_data(method, params, type):
            dct = {
                   "method" : method,
                   "params" : params,
                   "type" : type
                   }
            return dct

        keys = []

        method = 'baidu.ting.billboard.billList'
        for t in ['1', '2']:
            params = {
                'offset': '0',
                'size': '1000',
                'type': t
            }
            Scheduler.schedule(HotCrawler.type, key = method + t, data = generate_data(method, params, 'song_list'), interval = 3600)

        method = 'baidu.ting.plaza.getNewSongs'
        params = {
            'limit': '10000',
        }
        Scheduler.schedule(HotCrawler.type, key = method, data = generate_data(method, params, 'song_list'), interval = 3600)

        method = 'baidu.ting.album.getList'
        for i in ["0", "1", '2', '3', '4']:
            params = {
                'area': i,
                'order': '0',
                'style': '0',
                'is_recommend': '1',
                'offset': '0',
                'limit': '10000',
            }
            Scheduler.schedule(HotCrawler.type, key = method + i, data = generate_data(method, params, 'album_list'), interval = 3600)

        method = 'baidu.ting.diy.getOfficialDiyList'
        params = {
            'ver': '0',
            'type': '1',
            'pn': '0',
            'rn': '10000',
        }
        Scheduler.schedule(HotCrawler.type, key = method, data = generate_data(method, params, 'topic'), interval = 3600)


    def crawl(self):

        method = self.data['method']
        params = self.data['params']
        type = self.data['type']

        data = call_rest(method = method, params = params)

        if type == 'song_list':
            if data.get('song_list'):
                for songdata in data['song_list']:
                    song_id = int(songdata['song_id'])
                    album_id = int(songdata['album_id'])
                    artist_id = int(songdata['ting_uid'])
                    if album_id:
                        Scheduler.schedule(type = AlbumCrawler.type, key = str(album_id))
                    if artist_id:
                        Scheduler.schedule(type = ArtistCrawler.type, key = str(artist_id))
                    Scheduler.schedule(type = SongCrawler.type, key = str(song_id))
                    self.logger.info("song - %s" % song_id)

        elif type == 'album_list':
            if data.get('albumList'):
                for albumdata in data['albumList']:
                    album_id = int(albumdata['album_id'])
                    artist_id = int(albumdata['artist_ting_uid'])
                    if artist_id:
                        Scheduler.schedule(type = ArtistCrawler.type, key = str(artist_id))
                    Scheduler.schedule(type = AlbumCrawler.type, key = str(album_id))
                    self.logger.info("album - %s" % album_id)

        elif type == 'topic':
            if data.get('albumList'):
                for albumdata in data['albumList']:
                    code = albumdata['code']
                    try:
                        data = self.crawlTopic(code)
                    except Exception, e:
                        self.logger.error(e)
                        continue
                    if data.get('list'):
                        for songdata in data['list']:
                            song_id = int(songdata['song_id'])
                            album_id = int(songdata['album_id'])
                            artist_id = int(songdata['ting_uid'])
                            if album_id:
                                Scheduler.schedule(type = AlbumCrawler.type, key = str(album_id))
                            if artist_id:
                                Scheduler.schedule(type = ArtistCrawler.type, key = str(artist_id))
                            Scheduler.schedule(type = SongCrawler.type, key = str(song_id))
                            self.logger.info("song - %s" % song_id)


    def crawlTopic(self, code):
        method = 'baidu.ting.diy.getSongFromOfficalList'
        params = {
            'var': '0',
            'code': code,
        }
        data = call_rest(method = method, params = params)
        return data

class ArtistListCrawler(Crawler):

    type = "music.baidu.artistlist"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(ArtistListCrawler.type, interval = 86400)

    def crawl(self):
        method = "baidu.ting.artist.getList"
        offset = 0
        limit = 30
        while True:
            params = {
                      "order" : 1,
                      "offset" : offset,
                      "limit" : limit,
                      }
            data = call_rest(method = method, params = params)
            for artistdata in data['artist']:
                artist_id = artistdata['ting_uid']
                Scheduler.schedule(type = ArtistCrawler.type, key = str(artist_id), priority = Priority.Low, interval = 86400 * 7)
                self.logger.info("%s" % artist_id)

            total = int(data['nums'])
            offset += limit
            if offset >= total:
                break


class ArtistCrawler(Crawler):

    type = "music.baidu.artist"

    def crawl(self):
        artist_id = int(self.key)

        method = "baidu.ting.artist.getinfo"
        params = {
                  "tinguid" : artist_id
                  }
        dct = call_rest(method = method, params = params)
        self.export(dct)
        self.logger.info("%s" % artist_id)

        self.crawl_albums(artist_id)
        self.crawl_songs(artist_id)

    def crawl_albums(self, artist_id):
        offset = 0
        limits = 30
        method = "baidu.ting.artist.getAlbumList"

        while True:
            params = {
                      "tinguid" : artist_id,
                      "offset" : offset,
                      "limits" : limits,
                      }
            data = call_rest(method = method, params = params)

            for albumdata in data['albumlist']:
                album_id = int(albumdata['album_id'])
                Scheduler.schedule(type = AlbumCrawler.type, key = str(album_id), priority = Priority.Low)

            if not data.get('havemore'):
                break
            offset += limits


    def crawl_songs(self, artist_id):
        offset = 0
        limits = 50
        method = "baidu.ting.artist.getSongList"

        while True:
            params = {
                      "tinguid" : artist_id,
                      "offset" : offset,
                      "limits" : limits,
                      }
            data = call_rest(method = method, params = params)

            for songdata in data['songlist']:
                song_id = int(songdata['song_id'])
                Scheduler.schedule(type = SongCrawler.type, key = str(song_id), priority = Priority.Low)

            if not data.get('havemore'):
                break
            offset += limits

    def export(self, dct):
        data = MusicArtistModel({
                'source' : SOURCE,
                'source_id' : dct.get('ting_uid'),
                'title' : dct.get('name'),
                'description' : dct.get('intro'),
                'image' :dct.get('avatar_middle'),
                'url' : dct.get('url'),

  #              'weight' : dct.get('weight'),
                'region' : dct.get('country'),
                'birthday' : dct.get('birth'),
                'gender' : int(dct.get('gender')),
                })
        export(data)


class AlbumCrawler(Crawler):

    type = "music.baidu.album"

    def crawl(self):
        album_id = int(self.key)

        method = "baidu.ting.album.getAlbumInfo"
        params = {
                  "album_id" : album_id
                  }
        data = call_rest(method = method, params = params)

        songlist = data['songlist']
        album = data['albumInfo']

        self.export(album)
        self.logger.info("%s" % album_id)

        for songdata in songlist:
            Scheduler.schedule(type = SongCrawler.type, key = songdata['song_id'])

    def export(self, dct):
        visits = dct.get('hot')
        visits = int(visits) if visits else 0

        data = MusicAlbumModel({
                'source' : SOURCE,
                'source_id' : dct['album_id'],

                'artist' : dct.get('author'),
                'visits' : visits,
                'title' : dct.get('title'),
                'image' : dct.get('pic_big'),
                'time' : parse_date(dct.get('publishtime')),
                'description' : dct.get('info'),
                'genres' : dct.get('styles'),
                'language' : dct.get('language'),
                })

        export(data)


class SongCrawler(Crawler):

    type = "music.baidu.song"

    def crawl(self):
        song_id = int(self.key)

        method = "baidu.ting.song.getInfo"
        params = {
                  "songid" : song_id
                  }
        data = call_rest(method = method, params = params)

        song = data['songinfo']

#        try:
#            tags = self.crawl_tag(song_id)
#            song['tags'] = tags
#        except:
#            pass

        self.export(song)
        self.logger.info("%s" % song_id)

    def export(self, dct):
#     download_url, download_url_small = extract_downloadurl(dct['songurl'])

        visits = dct.get('hot')
        visits = int(visits) if visits else 0
        duration = dct.get('file_duration')
        duration = int(duration) if duration else 0

        data = MusicModel({
                'source' : SOURCE,
                'source_id' : dct['song_id'],
                'time' : parse_date(dct.get('publishtime')),
                'album' : dct.get('album_title'),
                'artist' : dct.get('author'),
                'visits' : visits,
                'title' : dct.get('title'),
                'duration' : duration,
                'image' : dct.get('pic_radio'),
                'url' : "http://music.baidu.com/song/%s" % dct['song_id'],
                'lyrics' : dct.get('lrclink'),
                'tags' : dct.get('tags'),

                'language' : dct.get('language'),
                })
        export(data)


    def crawl_tag(self, song_id):
        url = "http://music.baidu.com/song/%s" % song_id
        resp = downloader.download(url)
        hxs = HtmlXPathSelector(text  = resp.body)
        tags = hxs.select("//div[@class='song-info']//a[@class='tag-list']/text()").extract()
        return tags


    @staticmethod
    def extract_downloadurl(downloadinfo):
        infos = json.loads(downloadinfo).get('url')
        if not infos:
            return "", ""
        infos = sorted(infos, key = lambda item : item['file_size'])
        url_small = infos[0]['file_link']
        url = infos[-1]['file_link']
        return url, url_small


def merge_dct(todata, fromdata):
    for k, v in fromdata.iteritems():
        todata[k] = v
    return todata

if __name__ == "__main__":
    pass

