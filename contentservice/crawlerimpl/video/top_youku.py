#coding=utf8

import requests, HTMLParser
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoTopModel

TOP_youku= [{
            "url": 'http://index.youku.com/protop/2',
            "channel": u"电影",
            "source": u"优酷",
            "type": u"mv.youku.top",
            "priority": 2
            },
            {
            "url": "http://index.youku.com/protop/0" ,
            "channel": u"电视剧",
            "source": u"优酷",
            "type": "tv.youku.top",
            "priority": 2
            },
            {
             "url": "http://www.youku.com/v_olist/c_85_g__a__sg__mt__lg__q__s_1_r__u_0_pt_0_av_0_ag_0_sg__pr__h__p_%s.html",
             "channel": u"综艺",
             "source": u"优酷",
             "type": "zy.youku.top",
             "priority": 2
             },
            {
             "url": "http://news.youku.com/zt/hot",
             "channel": u"热点",
             "source": u"优酷-资讯",
             "type": "hot.youku.top",
             "priority": 3
             },
          ]

class TopCrawler(Crawler):
    type = "video.youku.top"
    recursive = True
    interval = 86400

    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 86400))

    def crawl(self):
        for spec in TOP_youku:
            rank_list = crawl_top(spec.get('url'),spec.get('channel'),50)
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
             
            
                
XPATH1={
       u'电影': "//div[@class='rank']/table/tbody//tr",
       u'电视剧': "//div[@class='rank']/table/tbody//tr",
       u'综艺': "//*[@id='listofficial']//div[@class='yk-col3']",
       u"热点": "//div[@class='yk-rank yk-rank-long']//div[@class='item']"
       }
XPATH2={
       u'电影': 'td[2]/a/text()',
       u'电视剧': 'td[2]/a/text()',
       u'综艺': "./div/div[4]/div[1]/a/@title",
       u"热点": "./a/text()"
        }

def crawl_top(url,channel,itemnum):
    currentPage = 1
    rank_list = []
    rank = 0
    while(True):
        currentUrl = (url % currentPage) if channel==u'综艺' else url
        hxs = load_html(currentUrl)
        for x in hxs.select(XPATH1.get(channel)):
            title = "".join(x.select(XPATH2.get(channel)).extract()[0].strip().split())
            rank+=1
            item = {'rank': rank,
                   'title': title,}
#             print "rank:%s title:%s"%(rank,title)
            rank_list.append(item)
            if rank>=itemnum:
                return rank_list
        currentPage+=1

def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text = data)

if __name__=='__main__':
    #crawl_top('http://www.youku.com/v_olist/c_100.html','动漫',20)
    TopCrawler().crawl()