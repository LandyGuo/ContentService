#coding=utf8
'''
http://www.v3gp.com/list.php?id=1
'''
import urllib2, re
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from contentservice.crawler import Crawler, export, Scheduler
from contentservice.models.ring import RingToneModel

SERVER = "http://www.v3gp.com"
SOURCE = "v3gp"

class RankListCrawler(Crawler):
    type = "ring.v3gp.ranklist"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(type = RankListCrawler.type, interval = 86400)

    def crawl(self):
        body = urllib2.urlopen(SERVER + "/list.php?id=1").read()
        body = unicode(body, 'gbk')
        hxs = HtmlXPathSelector(text = body)
        for s in hxs.select("//div[@id='vnav']/ul/li/a[contains(@href, 'list.php')]"):
            link = s.select("@href").extract()[0]
            list_id = re.findall("id=(\d+)", link)[0]
            name = s.select("text()").extract()[0]
            data = {
                    "id" : list_id,
                    "name" : name,
                    }
            Scheduler.schedule(RankCrawler.type, key = list_id, data = data, interval = 86400)


class RankCrawler(Crawler):
    type = "ring.v3gp.rank"

    def crawl(self):
        keys = []
        page = 1
        while True:
            url = SERVER + "/list.php?id=%s&page=%s" % (self.key, page)
            body = urllib2.urlopen(url).read()
            body = unicode(body, 'gbk')
            hxs = HtmlXPathSelector(text = body)
            for s in hxs.select("//div[@id='ll']/ul"):
                try:
                    play_js = s.select("li[@class='ll-t']/a/@onclick").extract()[0]
                    play_id = re.findall("list_play\('(.+)'\)", play_js)[0]
                    name = s.select("li[@class='ll-n']/a/text()").extract()[0]
                    id = re.findall("/(.+)\.html", s.select("li[@class='ll-n']/a/@href").extract()[0])[0]
                    duration = int(re.findall("(\d+)", s.select("li[@class='ll-c']/text()").extract()[0])[0])
                    albums = s.select("li[@class='ll-z']/a/text()").extract()
                    album = albums[0] if albums else ""

                    data = {
                            "id" : id,
                            "play_id" : play_id,
                            "title" : name,
                            "duration" : duration,
                            "album" : album,
                            }

                    keys.append(RingToneModel(title = name)['key'])
                    Scheduler.schedule(RingCrawler.type, key = id, data = data)
                except:
                    pass
            page_text = hxs.select("//div[@id='ll']/div[@class='cpage']/text()").extract()[-1]
            page_total = int(re.findall(u"(\d+)页", page_text)[0])
            if page >= page_total:
                break
            page += 1


class RingCrawler(Crawler):
    type = "ring.v3gp.ring"

    def crawl(self):
        body = urllib2.urlopen(SERVER + "/play.php?file=%s" % self.data["play_id"]).read()
        xxs = XmlXPathSelector(text = body)
        url = xxs.select("//player/audio/track/@url").extract()[0]
        ringtone = RingToneModel({
                                  "source" : SOURCE,
                                  "source_id" : self.data["id"],
                                  "title" : self.data["title"],
                                  "duration" : self.data["duration"],
                                  "album" : self.data.get("album"),
                                  "url" : url,
                                  })
        export(ringtone)

if __name__ == "__main__":
    RankCrawler(key = "1").crawl()
    RankCrawler(key = "2").crawl()

