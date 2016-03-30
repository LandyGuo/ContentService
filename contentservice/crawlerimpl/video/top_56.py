#coding=utf8
import requests, HTMLParser, simplejson, urllib,re
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoTopModel


TOP_56= [
            {
            "url": "http://fun.56.com/paiHang/?do=ajaxVideos&type=rank&t=w&part=%s&&callback=jnsJsonpData4" ,
            "channel": u"搞笑",
            "source": u"56",
            "type": "gx.56.top",
            "priority": 3
            },  
           ]

class TopCrawler(Crawler):
    
    type = "video.56.top"
    interval = 86400

    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 86400))

    def crawl(self):
        for spec in TOP_56:
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
    currentPage = 1
    while(True):
        specs = jsonLoad(url%currentPage)
        for x in specs:
            title = x.get('title',"").strip()
            rank+=1
            item = {'rank': rank,
                   'title': title}
#             print "rank:%s title:%s"%(rank,title)
            rank_list.append(item)
            if rank>=itemnum:
                return rank_list
        currentPage+=1
     
def jsonLoad(url):
    resp = requests.get(url)
    prefix = "jnsJsonpData4("
    suffix = ")"
    return simplejson.loads(resp.text.lstrip(prefix).rstrip(suffix))
     
if __name__=='__main__':
    TopCrawler().crawl()