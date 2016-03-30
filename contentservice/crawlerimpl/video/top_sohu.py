#coding=utf8

import requests, HTMLParser
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoTopModel


TOP_sohu= [
#            {
#             "url": 'http://so.tv.sohu.com/list_p1101_p2_p3_p4_p5_p6_p7_p8_p9.html',
#             "channel": u"电视剧",
#             "type": "tv.sohu.top",
#             "priority": 6
#             },
            {
            "url": "http://so.tv.sohu.com/list_p1106_p20_p3_p4_p5_p6_p77_p8_p9_2d1_p10%s_p110.html" ,
            "channel": u'综艺',
            'source': u'搜狐-周播放最多',
            "type": "zy.sohu.top",
            "priority": 3
            },
            {
            "url": "http://tv.sohu.com/hotcomic/" ,
            "channel": u'动漫',
            "source": u'搜狐',
            "type": "dm.sohu.top",
            "priority": 2
            },
            {
            "url": "http://tv.sohu.com/hotnews/" ,
            "channel": u'热点',
            'source': u'搜狐-新闻',
            "type": "xw.sohu.top",
            "priority": 1
            },
            {
            "url": "http://tv.sohu.com/hotyule" ,
            "channel": u'热点',
            'source': u'搜狐-娱乐',
            "type": "yl.sohu.top",
            "priority": 2
            },
          ]

class TopCrawler(Crawler):
    
    type = "video.sohu.top"
    interval = 86400

    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 86400))

    def crawl(self):
        for spec in TOP_sohu:
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
 
def crawl_top(url,channel,itemnum):
    if channel==u'动漫':
        return crawlDmTop(url,itemnum)
    if channel==u"热点":
        return crawlHotTop(url,itemnum)
    rank_list = []
    rank = 0    
    currentPage = 1
    while(True):
        url1 = url % currentPage 
        hxs = load_html(url1)
        for x in hxs.select("//div[@class='column-bd clear']//li[@class='clear']"):
            title = x.select('div[2]/div/p[1]/a/text()').extract()[0].strip()
            title = ''.join(title.split())
            rank+=1
            item = {'rank': rank,
                   'title': title,}
#             print 'rank:%s title:%s'%(rank,title)
            rank_list.append(item)
            if rank>=itemnum:
                return rank_list
        currentPage += 1
'''
http://tv.sohu.com/hotnews/
http://tv.sohu.com/hotyule/
'''
def crawlHotTop(url,itemnum):
    rank = 0
    rank_list = []
    hxs = load_html(url)
    for x in hxs.select(r"//ul[@class='rList']//li"):
        title = x.select("./div[@class='vName']/div/a/text()").extract()[0]
        title = "".join(title.strip().split())
        rank+=1
#         print "rank:%s title:%s"%(rank,title)
        item = {
                "rank": rank,
                "title": title,}
        rank_list.append(item)
        if rank>=itemnum:
            return rank_list
    
def crawlDmTop(url,itemnum):
    rank = 0
    rank_list = []
    hxs = load_html(url) 
    firstTitle = "".join(hxs.select("//*[@id='content']/div[2]/div[2]/div[2]/ul[2]/li[1]/div[1]/div/a/text()").extract()[0].strip().split())
    rank+=1
    item = {'rank':rank,'title':firstTitle}
#     print 'rank:%s title:%s'%(rank,firstTitle)
    rank_list.append(item)
    for x in hxs.select("//div[@class='rList_subCon']//li"):
        try:
            title = "".join(x.select(".//div[@class='vName']/div/a/text()").extract()[0].strip().split())
            rank += 1
#             print 'rank:%s title:%s'%(rank,title)
            rank_list.append({'rank':rank,'title':title})
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
    #crawl_top('http://so.tv.sohu.com/list_p1101_p2_p3_p4_p5_p6_p7_p8_p9.html',20)
    TopCrawler().crawl()
#     crawlHotTop("http://tv.sohu.com/hotnews/",50)