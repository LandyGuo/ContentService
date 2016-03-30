#coding=utf8
import requests, re
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, export, Priority, Scheduler
from contentservice.models.ring import RingBackRankModel, RingToneModel, RingToneRankModel

WORANK_MAP = {
              u"网络红歌" : {
                         "title" : u"网络红歌",
                         "type" : u"webhot",
                         "ringtone" : True,
                         "ringback" : [],
                         }
              }
SOURCE = 'cu'

'''
http://mv.wo.com.cn/song/index.htm
'''
class WoRankCrawler(Crawler):

    type = 'ring.unicom.worank'

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(WoRankCrawler.type, priority = Priority.High, interval = 86400)

    def crawl(self):
        text = requests.get('http://mv.wo.com.cn/song/index.htm').text
        hxs = HtmlXPathSelector(text = text)
        for s in hxs.select("//div[@class='filtpad']/p/a[contains(@value, 'songBoardList')]"):
            try:
                value = s.select("@value").extract()[0]
                board_id = re.findall("(\d+)\.htm", value)[0]
                title = s.select("text()").extract()[0]
                self.crawl_list(board_id, title)
            except Exception, e:
                self.logger.warning(e)

    def crawl_list(self, board_id, board_title):
        if not WORANK_MAP.get(board_title):
            return

        keys = []
        page = 1
        while True:
            url = 'http://mv.wo.com.cn/songBoardList/index_%s-BOARD-%s.htm' % (page, board_id)
            text = requests.get(url).text
            hxs = HtmlXPathSelector(text = text)
            for s in hxs.select("//tbody[@id='ringSaleList']/tr"):
                try:
                    title = s.select("td[@class='songname']/a/span/text()").extract()[0]
                    artist = s.select("td[@class='singtd']/a/text()").extract()[0]
                    artist = artist.split("+")[0]
                    key = RingToneModel({"title" : title, "artist" : artist})["key"]
                    keys.append(key)
                except:
                    pass

            has_next = False
            for text in s.select("//p[@class='inlinepages']/a/text()").extract():
                if text.find(u"下一页") != -1:
                    has_next = True
                    break

            if not has_next:
                break
            page += 1


        rank = WORANK_MAP[board_title]
        if rank['ringtone']:
            export(RingToneRankModel({
                               'source' : SOURCE,
                               'type' : rank['type'],
                               'title' : rank['title'],
                               'ringtones' : keys,
                               }))
        for carrier in rank['ringback']:
            export(RingBackRankModel({
                                'source' : SOURCE,
                                'carrier' : carrier,
                                'type' : rank['type'],
                                'title' : rank['title'],
                                'ringbacks' : keys,
                                      }))

if __name__ == "__main__":
    WoRankCrawler().crawl()

