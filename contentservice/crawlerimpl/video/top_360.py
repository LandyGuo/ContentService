#coding=utf8
import requests,HTMLParser
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoTopModel




TOP_360= [
#           {
#             "url": 'http://v.360.cn/dianying/list.php?cat=all&year=all&area=all&act=all',
#             "channel": u"电影",
#             "type": "mv.360.top",
#             "priority": 2
#             },
            {
            "url": "http://v.360.cn/dianshi/list.php?pageno=%s" ,
            "channel": u"电视剧",
            "source": u"360影视",
            "type": "tv.360.top",
            "priority": 1
            },
#             {
#              "url": "http://v.360.cn/dongman/list.php",
#              "channel": u"动漫",
#              "type": "dm.360.top",
#              "priority": 2
#              }
          ]

class TopCrawler(Crawler):
    
    type = "video.360.top"
    interval = 86400

    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 86400))

    def crawl(self):
        for spec in TOP_360:
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
        hxs = load_html(url%currentPage)
        for x in hxs.select("//div[@class='result-view']/ul//li"):
            title = "".join(x.select('div[2]/p[1]/a/text()').extract()[0].strip())
            rank+=1
            item = {'rank': rank,
                   'title': title}
#             print 'rank:%s title:%s'%(rank,title)
            rank_list.append(item)
            if rank>=itemnum:
                return rank_list
        currentPage += 1
    

def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text = data)
        


if __name__=='__main__':
    TopCrawler().crawl()