# -*- coding: utf-8 -*-
import re, urllib, json
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from contentservice.models.music import MusicModel, MusicAlbumModel, MusicArtistModel
from contentservice.utils.datetimeutil import parse_date
from contentservice.crawler import Crawler, export, Scheduler
from contentservice.utils import downloader, get_exception_info

DOMAIN = 'http://www.xiami.com'
RANK_URL = DOMAIN + '/music/hot'

SOURCE = "xiami"

def download(resp):
    if isinstance(resp, downloader.Response):
        return resp

    url = str(resp)
    if not url.startswith('http://'):
        url = DOMAIN + url

    resp = downloader.download(url)
    return resp

class HotCrawler(Crawler):

    type = "music.xiami.hot"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(HotCrawler.type, interval = 86400)

    def crawl(self):
        all_recent_chart_urls = []

        # get chart urls.
        chart_urls = self.get_chart_urls()

        # get recent urls for each chart.
        for chart_url in chart_urls:
            recent_chart_urls = self.get_recent_urls(chart_url)
            all_recent_chart_urls.append(recent_chart_urls)

        # get music info.
        for recent_chart_urls in all_recent_chart_urls:
            for chart_url in recent_chart_urls:
                self.extract_songs(chart_url)


    def extract_songs(self, url):
        resp = download(url)
        hxs = HtmlXPathSelector(text = resp.body)
        elements = hxs.select('//td[@class="song_name"]/a')
        for i in range(len(elements)):
            element = elements[i]
            try:
                href = element.select('@href').extract()[0].strip()
                match = re.findall('song/(\d+)', href)
                if len(match) == 0:
                    continue
                song_id = int(match[0])
                Scheduler.schedule(SongCrawler.type, key = str(song_id))
            except:
                self.logger.error(get_exception_info())

    def get_chart_urls(self):
        url = RANK_URL
        resp = download(url)
        hxs = HtmlXPathSelector(text = resp.body)
        hrefs = hxs.select('//span[@class="x_more"]/a/@href').extract()
        return hrefs

    def get_recent_urls(self, url):
        resp = download(url)
        hxs = HtmlXPathSelector(text = resp.body)
        elements = hxs.select('//select[@name="amount"]/option/@value').extract()

        urls = []
        if resp.body.find('/time_week/') > -1:
            fmt = '%s/time_week/%s'
        else:
            fmt = '%s/b/%s'
        for i in elements:
            urls.append(fmt % (url, i))

        return urls

class SongCrawler(Crawler):

    type = "music.xiami.song"

    def crawl(self):
        song_id = int(self.key)

        song = {}

        url = "/song/%d" % song_id
        resp = download(url)
        hxs = HtmlXPathSelector(text = resp.body)

        song['id'] = song_id
        song['name'] = hxs.select("//div[@id='title']/h1/text()").extract()[0].strip()
        song['image_link'] = hxs.select("//a[@id='albumCover']/img/@src").extract()[0].strip()

        s = hxs.select("//table[@id='albums_info']")
        song['album_name'] = s.select(".//a[contains(@href, '/album/')]/text()").extract()[0]

        album_link = s.select(".//a[contains(@href, '/album/')]/@href").extract()[0]
        song['album_id'] = int(re.match("/album/(\d+)", album_link).group(1))

        artist_s = s.select(".//a[contains(@href, '/artist/')]")
        if artist_s:
            song['artist_name'] = artist_s.select("text()").extract()[0]
            artist_link = artist_s.select("@href").extract()[0]
            song['artist_id'] = int(re.findall("artist/(\d+)", artist_link)[0])
        else:
            artist_s = s.select(".//a[contains(@href, 'find?artist=')]")
            if artist_s:
                song['artist_name'] = artist_s.select("text()").extract()[0]
                artist_link = artist_s.select("@href").extract()[0]
                try:
                    fp = urllib.urlopen(url = DOMAIN + artist_link)
                    song['artist_id'] = int(re.findall("artist/(\d+)", fp.geturl())[0])
                except:
                    self.logger.info("Get artist_id failed for song - %d" % song_id)

        song['visits'] = get_playcount("song", song_id, self.logger)

        url = '/song/playlist/id/%d/object_name/default/object_id/0' % (song_id)
        resp = download(url)
        data = re.sub('xmlns="[^"]*"', '', resp.body)
        xxs = XmlXPathSelector(text = data)

        try:
            lyrics_link = xxs.select('//lyric/text()').extract()[0]
            song['lyrics'] = lyrics_link
            #song['lyrics'] = download(lyrics_link).body
        except:
            pass

        try:
            tags = self.crawl_tag(song_id)
            song['tags'] = tags
        except:
            pass

        if song.get('artist_id'):
            Scheduler.schedule(type = ArtistCrawler.type, key = str(song['artist_id']))
        if song.get('album_id'):
            Scheduler.schedule(type = AlbumCrawler.type, key = str(song['album_id']))

        self.export(song)


    def crawl_tag(self, song_id):
        url = "http://www.xiami.com/song/moretags/id/%s" % song_id
        resp = download(url)
        hxs = HtmlXPathSelector(text = resp.body)
        tags = hxs.select("//div[@id='tag_cloud']/span/a/text()").extract()
        return tags


    def export(self, song):
        model = MusicModel({
                'source' : SOURCE,
                'source_id' : song['id'],
                "title" : song['name'],
           #     "time" : datetime.min,
                "visits" : song['visits'],
                "image" : song["image_link"],
                "url" : "http://www.xiami.com/song/%s" % song['id'],
                "tags" : song['tags'],
                "artist" : song['artist_name'],
                "album" : song['album_name'],
             })
        export(model)


class AlbumCrawler(Crawler):

    type = "music.xiami.album"

    def crawl(self):
        data = {}
        album_id = int(self.key)
        data['id'] = album_id

        url = "/album/%d" % album_id
        resp = download(url)
        hxs = HtmlXPathSelector(text = resp.body)

        data['name'] = hxs.select("//div[@id='title']/h1/text()").extract()[0].strip()
        s = hxs.select("//div[@id='album_info']")
        data['artist_name'] = s.select("table/tr/td/a[contains(@href, 'artist/')]/text()").extract()[0]
        artist_link = s.select("table/tr/td/a[contains(@href, 'artist/')]/@href").extract()[0]
        data['artist_id'] = int(re.match("/artist/(\d+)", artist_link).group(1))
        tabletext = s.select("table").extract()[0]
        date = re.findall(u"(\d+年\d+月\d+日)", tabletext)
        if date:
            data['date'] = parse_date(date[0])
        visit = 0
        for song_hot in hxs.select("//td[@class='song_hot']/text()").extract():
            visit += int(song_hot)
        data['visit'] = visit
        data['image_link'] = hxs.select("//div[@id='album_cover']/a[@id='cover_lightbox']/@href").extract()[0]
        data['description'] = "\n".join(hxs.select("//div[@id='album_intro']/div[@class='album_intro_brief']/span/text()").extract())
        if not data['description'].strip():
            data['description'] = "\n".join(hxs.select("//div[@id='album_intro']/div[@class='album_intro_brief']/span/div/text()").extract())

        for s in hxs.select("//div[@id='album_info']/table/tr"):
            texts = s.select("td/text()").extract()
            if not texts:
                continue
            if texts[0].find(u"语种") != -1:
                data['language'] = texts[1]
            elif texts[0].find(u"专辑风格") != -1:
                data['genres'] = texts[1]

        if data.get('artist_id'):
            Scheduler.schedule(type = ArtistCrawler.type, key = str(data['artist_id']))

        for song_link in hxs.select("//table[@class='track_list']//tr/td[@class='song_name']/a/@href").extract():
            song_id = int(re.match("/song/(\d+)", song_link).group(1))
            Scheduler.schedule(type = SongCrawler.type, key = str(song_id))

        self.export(data)

    def export(self, data):
        model = MusicAlbumModel({
                'source' : SOURCE,
                'source_id' : data['id'],
                "title" : data['name'],
                "time" : data.get('date'),
                "image" : data.get('image_link'),
                "description" : data.get('description'),
                "artist" : data.get('artist_name'),
                "visits" : data.get('visit'),

                "language" : data.get('language'),
                "genres" : data.get('genres'),
             })
        export(model)

class ArtistCrawler(Crawler):

    type = "music.xiami.artist"

    def crawl(self):
        artist_id = int(self.key)
        url = "/artist/%d" % artist_id
        resp = download(url)
        hxs = HtmlXPathSelector(text = resp.body)

        visits = get_playcount("artist", artist_id, self.logger)
        data = {
                'id' : artist_id,
                'name' : hxs.select("//div[@id='title']/h1/text()").extract()[0].strip(),
                'image_link' : hxs.select("//div[@id='artist_photo']/a[@id='cover_lightbox']/@href").extract()[0],
                'visits' : visits,
                }
        self.export(data)

    def export(self, data):
        model = MusicArtistModel({
                "source" : SOURCE,
                "source_id" : data['id'],

                "title" : data['name'],
                "visits" : data['visits'],
                "image" : data['image_link'],
             })
        export(model)

def get_playcount(type, id, logger):
    try:
        resp = download("/count/getplaycount?id=%s&type=%s" % (id, type))
        return json.loads(resp.body)["plays"]
    except:
        logger.warning("Get play count failed, %s %s" % (type, id))
        return 0

if __name__ == "__main__":
    pass

