#coding=utf8
import requests,HTMLParser
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoTopModel


TOP_tudou= [
            {
            "url": "http://www.tudou.com/top/r9c0t.html" ,
            "channel": u"动漫",
            "source": u"土豆",
            "type": "dm.tudou.top",
            "priority": 1
            },  
           ]

class TopCrawler(Crawler):
    
    type = "video.tudou.top"
    interval = 86400

    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 86400))

    def crawl(self):
        for spec in TOP_tudou:
            rank_list = crawl_top(spec.get('url'),50)
#             print 'source:%s channel:%s priority:%s num:%s'%(spec['source'],spec['channel'],spec['priority'],len(rank_list))
            rank = VideoTopModel({
                                  'source': spec['source'],
                                  'type': spec['type'],
                                  'channel': spec['channel'],
                                  'priority': spec['priority'],
                                  'updatetime': datetime.now().isoformat(),
                                  'list': rank_list
                                 })
            export(rank)
            
 
def crawl_top(url,itemnum):
    rank_list = []
    rank = 0
    hxs = load_html(url)
    for x in hxs.select("./body/.//div[@class='title']"):
        title = "".join(x.select('./a/@title').extract()[0].strip().split())
        rank+=1
        item = {'rank': rank,
               'title': title}
#         print 'rank:%s title:%s'%(rank,title)
        rank_list.append(item)
        if rank>=itemnum:
            return rank_list
    

def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "gbk"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text = data)
        


if __name__=='__main__':
    TopCrawler().crawl()