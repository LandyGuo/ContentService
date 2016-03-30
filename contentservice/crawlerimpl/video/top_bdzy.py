#coding=utf8
import requests, urlparse, HTMLParser, simplejson, urllib
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority,export
from contentservice.models.video import VideoTopModel

BAIDU_SERVER = "http://v.baidu.com"


TOP_baidu= [{
            "path": "commonapi/movie2level/",
            "channel": u"电影",
            "source": u"百度视频",
            "type": "mv.bdzy.top",
            "priority": 1
            },
            {
            "path": "commonapi/tvshow2level/",
            "channel": u"综艺",
            "source": u"百度视频",
            "type": "zy.bdzy.top",
            "priority": 1
            },
            {
             "path": "commonapi/comic2level/",
             "channel": u"福利",
             "source": u"百度视频-美女",
             "type": "fl.bdzy.top",
             "priority": 3
             }
          ]

class TopCrawler(Crawler):
    
    type = "video.bdzy.top"
    interval = 86400

    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(TopCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 86400))

    def crawl(self):
        for spec in TOP_baidu:
            rank_list = crawl_top(spec['channel'],spec.get('path'),50)
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


def crawl_top(channel,path,itemnum):
    if channel==u'福利':
        return getBeauty(itemnum)
    params = {'pn':1}
    videolist = get_api(params,path)
    rank_list = []
    rank = 0
    while(True):
        for video in videolist.get('videos'):
            title = "".join(video.get('title').strip().split())
            rank+=1
            item = {'rank':rank,
                   'title':title}
#             print 'channel:%s  rank:%s title:%s'%(channel,rank,title)
            rank_list.append(item)
            if rank>=itemnum:
                return rank_list
        params['pn']+=1
        videolist = get_api(params,path)
        
def getjsonHead(url):
    hxs = load_html(url)
    script = hxs.select(r".//script[@type='text/javascript'][last()-5]/text()").extract()[0]
    jsonList = script.split('dataCenter.push(')[1].split(')')[0]
    return simplejson.loads(jsonList)
    
def getBeauty(itemnum):
    currentPage = 1
    rank = 0
    rank_list = []
    while(True):
        url = getjsonUrl(currentPage)
        itemList = getjsonHead(url) if currentPage==1 else getjson(url)
        for item in itemList:
            title = "".join(item['title'].strip().split())
            rank+=1
            rank_item = {'rank': rank,
                         'title':title,}
#             print 'rank:%s title:%s'%(rank,title)
            rank_list.append(rank_item)
            if rank>=itemnum:
                return rank_list
        currentPage+=1

def getjson(url):
    resp = requests.get(url)
    resp.encoding = 'gbk'
    json_str = prejsonStr(resp.text.strip())
    return simplejson.loads(json_str)
    
    
def prejsonStr(json_format_str):
    prefix = "json1390202196681("
    suffix = ");"
    return json_format_str.lstrip(prefix).rstrip(suffix)

def getjsonUrl(page):    
    server = "http://v.baidu.com/square/"
    param=[ 'sort=hot',
            'tag=%s'%urllib.quote(u'美女'.encode('gbk')),
            'p=%s'%page,
            'callback=json1390202196681']
    return  server+'?'+'&'.join(param)
    
def get_api(params,path):
    url = urlparse.urljoin(BAIDU_SERVER, path)
    resp = requests.get(url,params=params)
    return resp.json().get('videoshow')

def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "gbk"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text = data)
    
if __name__=='__main__':
    TopCrawler().crawl()