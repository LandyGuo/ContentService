#coding=utf8
import requests, HTMLParser, simplejson, urllib,re
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoTopModel

 
TOP_56= [
            {
            "url": "http://api.dp.sina.cn/interface/i/cms/video_column.php" ,
            "channel": u"福利",
            "source": u"新浪",
            "type": "fl.sina.top",
            "priority": 2
            },  
           ]

class TopCrawler(Crawler):
    
    type = "video.sina.top"
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
        specs = callApi(url,currentPage)
        for x in specs:
            title = x.get('title',"").strip()
            title = "".join(title.split())
            rank+=1
            item = {'rank': rank,
                   'title': title}
#             print "rank:%s title:%s"%(rank,title)
            rank_list.append(item)
            if rank>=itemnum:
                return rank_list
        currentPage+=1

def callApi(url,page):
    param =dict([('page',page),
                 ('param','c0n297644'),
                 ('num',15),
                 ('jsoncallback','loadCallbackFunction'),
                 ('callback','jsonp2')])
    resp = requests.get(url,params=param)
    json_str =  jsonprocess(resp.text)
    return simplejson.loads(json_str).get('data',[])
   
def jsonprocess(json_format_str):
    prefix = 'loadCallbackFunction('
    suffix = ');'
    return json_format_str.lstrip(prefix).rstrip(suffix)     

     
if __name__=='__main__':
    TopCrawler().crawl()
#     callApi("http://api.dp.sina.cn/interface/i/cms/video_column.php")