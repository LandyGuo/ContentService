#coding=utf8
import requests, HTMLParser
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoTopModel

TOP_douban= [{
            "url": 'http://movie.douban.com/chart',
            "channel": u"电影",
            "type": "mv.douban.top",
            "source": u"豆瓣",
            "priority": 5,
            "max_num": 10
            },
#             {
#             "url": "http://movie.douban.com/tv/" ,
#             "channel": u"电视剧",
#             "type": "tv.douban.top",
#             "source": u"豆瓣-电视剧新片榜",
#             "priority": 3,
#             'max_num': 20
#             }
          ]

class TopCrawler(Crawler):
    type = "video.douban.top"
    recursive = True
    interval = 86400

    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 86400))

    def crawl(self):
        for spec in TOP_douban:
            rank_list = crawl_top(spec.get('url'),spec.get('max_num'))
#             print 'source:%s channel:%s priority:%s num:%s'%(spec['source'],spec['channel'],spec['priority'],len(rank_list))
            rank = VideoTopModel({
                                  'source': spec['source'],
                                  'channel': spec['channel'],
                                  'priority': spec['priority'],
                                  'type': spec['type'],
                                  'updatetime': datetime.now().isoformat(),
                                  'list': rank_list
                              })
            export(rank)
            

def crawl_top(url,itemnum):
    hxs = load_html(url)
    rank_list = []
    rank = 0
    for x in hxs.select("//div[@class='indent']//table"):
        title = x.select('tr/td[2]/div/a[1]/text()').extract()[0].strip()
        title = ''.join(title.split())
        title = title.replace('/', '') if title.endswith('/') else title
        rank+=1
        item = {'rank':rank,
              'title':title,}
#         print 'rank:%s title:%s'%(rank,title)
        rank_list.append(item)
        if rank>=itemnum:
            return rank_list
    

def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text = data)
        


if __name__=='__main__':
    #crawl_top('http://movie.douban.com/tv/',20)
    TopCrawler().crawl()