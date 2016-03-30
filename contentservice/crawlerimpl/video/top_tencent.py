#coding=utf8

import requests, HTMLParser
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoTopModel


TOP_tencent= [
#               {
#                "url": 'http://v.qq.com/cartlist/0/3_-1_-1_-1_-1_1_0_0_20.html',
#                "channel": u"动漫",
#                "type": "dm.tencent.top",
#                "priority": 5
#               },
              {
               "url": 'http://v.qq.com/rank/detail/1_-1_-1_-1_2_-1.html',
               "channel": u"电影",
               'source': u'腾讯视频',
               "type": "dy.tencent.top",
               "priority": 4
              },
              {
               "url": 'http://v.qq.com/hotshare/list/rxlist_0_0_3_%s.html',
               "channel": u"搞笑",
               'source': u'腾讯',
               "type": "gx.tencent.top",
               "priority": 2
              },
                   
             ]

class TopCrawler(Crawler):
    type = "video.tencent.top"
    recursive = True
    interval = 86400

    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 86400))

    def crawl(self):
        for spec in TOP_tencent:
            rank_list = crawl_top(spec.get('url'),spec['channel'],50)
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

def crawl_top(url,channel,itemnum):
    if channel==u'搞笑':
        return crawlGx(url,itemnum)
    hxs = load_html(url)
    rank_list = []
    rank = 0
    for x in hxs.select("//*[@id='mod_list']//li"):
        title = x.select('./span[2]/a/text()').extract()[0].strip()
        title = ''.join(title.split()) 
        rank+=1
        item = {
               'rank': rank,
               'title': title,}
#         print 'rank:%s title:%s'%(rank,title)
        rank_list.append(item)
        if rank>=itemnum:
            return rank_list

def crawlGx(url,itemnum):
    currentPage = 1
    rank_list = []
    rank = 0
    while(True):    
        hxs = load_html(url%currentPage)
        for x in hxs.select("//ul[@class='mod_list_pic_160']//li"):
            title = x.select("./h6/a/text()").extract()[0].strip()
            title = ''.join(title.split()) 
            rank+=1
            item = {'rank':rank,'title':title}
#             print 'rank:%s title:%s'%(rank,title)
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
    #crawl_top('http://v.qq.com/cartlist/0/3_-1_-1_-1_-1_1_0_0_20.html',20)
    TopCrawler().crawl()