#coding=utf8

import requests, HTMLParser
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoTopModel


TOP_letv= [{
            "url": 'http://top.letv.com/filmhp.html',
            "channel": u"电影",
            "source": u"乐视",
            "type": "mv.letv.top",
            "priority": 3
            },
           {
            "url": 'http://top.letv.com/comichp.html',
            "channel": u"动漫",
            "source": u"乐视",
            "type": "dm.letv.top",
            "priority": 4
            },
            {
            "url": 'http://top.letv.com/enthp.html',
            "channel": u"热点",
            "source": u"乐视-娱乐",
            "type": "hot.letv.top",
            "priority": 4
            },
          ]

class TopCrawler(Crawler):
    type = "video.letv.top"
    recursive = True
    interval = 86400

    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval',86400))

    def crawl(self):
        for spec in TOP_letv:
            rank_list = crawl_top(spec.get('url'),50)
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
    for x in hxs.select("//div[@class='chart-data section1']/ol[1]//li[not(@class)]"):
        try:
            title = x.select('span[2]/a/text()').extract()[0].strip()
            title = ''.join(title.split()) 
            rank+=1
            item = {
                  'rank': rank,
                  'title': title,}
#             print 'rank:%s title:%s'%(rank,title)
            rank_list.append(item)
            if rank>=itemnum:
                return rank_list
        except:
            pass
    

def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text = data)
        


if __name__=='__main__':
    #crawl_top('http://top.letv.com/filmhp.html',20)
    TopCrawler().crawl()