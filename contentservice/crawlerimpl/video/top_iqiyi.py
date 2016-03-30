#coding=utf8

import requests, HTMLParser
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoTopModel


TOP_iqiyi= [{
            "url": 'http://top.iqiyi.com/zongyi.html',
            "channel": u"综艺",
            "type": "zy.iqiyi.top",
            "source": u"爱奇艺-热播",
            "priority": 4
            },
            {
            "url": "http://top.iqiyi.com/dianshiju.html" ,
            "channel": u"电视剧",
            "type": "tv.iqiyi.top",
            "source": u"爱奇艺-热播",
            "priority": 3
            },
            {
            "url": "http://top.iqiyi.com/dongman.html" ,
            "channel": u"动漫",
            "type": "dm.iqiyi.top",
            "source": u"爱奇艺",
            "priority": 3
            },
            {
            "url": "http://top.iqiyi.com/zixun.html" ,
            "channel": u"热点",
            "type": "zx.iqiyi.top",
            "source": u"爱奇艺-咨讯",
            "priority": 5
            },
            {
            "url": "http://top.iqiyi.com/yule.html" ,
            "channel": u"热点",
            "type": "yl.iqiyi.top",
            "source": u"爱奇艺-娱乐",
            "priority": 6
            },
            {
            "url": "http://top.iqiyi.com/gaoxiao.html" ,
            "channel": u"搞笑",
            "type": "gx.iqiyi.top",
            "source": u"爱奇艺",
            "priority": 1
            },
            {
            "url": "http://top.iqiyi.com/weidianying.html" ,
            "channel": u"福利",
            "type": "fl.iqiyi.top",
            "source": u"爱奇艺-微电影",
            "priority": 1
            },
          ]

class TopCrawler(Crawler):
    
    type = "video.iqiyi.top"
    
    interval = 86400

    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval',86400))

    def crawl(self):
        for spec in TOP_iqiyi:
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
    for x in hxs.select("//*[@id='tab_top50']/div[1]/ul//li"):
        title = "".join(x.select('a[1]/@title').extract()[0].strip().split())
        rank+=1
        item={'rank': rank,
              'title': title}
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
    #crawl_top('http://top.iqiyi.com/index/top50.htm?cid=1&dim=day',20)
    TopCrawler().crawl()