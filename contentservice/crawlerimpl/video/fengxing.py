#coding=utf8
import urllib, json, re, logging
from datetime import datetime
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoSourceModel, VideoItemModel
from contentservice.utils.datetimeutil import parse_date

logger = logging.getLogger('contentservice')

'''
从网页的json包中获取视频信息
'''

LIST = "http://jsonfe.funshion.com/list/?cli=aphone&ver=0.0.0.1&ta=0&type=%s&pagesize=24\
      &page=%s&cate=all&region=all&rdate=all&karma=all&udate=all&order=pl"
      
DETAIL = "http://jsonfe.funshion.com/media/?cli=aphone&ver=0.0.0.1&ta=0&mid=%s"

MOVIE_PLAY = "http://m.funshion.com/play?mediaid=%s"

PLAY_URL = "http://m.funshion.com/play?mediaid=%s&number=%s"

SOURCE = 'fengxing'

CHANNELS = [u'电影',u'电视剄1�7',u'综艺',u'动漫']

DICT={
        u"电影": "movie",
        u"电视剄1�7": "tv",
        u"综艺": "variety",
        u"动漫": "cartoon"
        }

class ListCrawler(Crawler):
    
    type = 'video.fengxing.list'
    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(
                           ListCrawler.type, #爬虫类型
                           key = "", #该类型只有一个实侄1�7,key讄1�7""
                           priority = conf.get('priority', Priority.High), #优先级为髄1�7
                           data = {'updated' : datetime.min}, #附加数据为上次爬取到的最新视频的更新时间
                           interval = conf.get('interval', 3600) #循环抓取间隔丄1�7�时
                           )
    def crawl(self):
        for channel in CHANNELS:            
            list_url=LIST % (DICT.get(channel), 1)#进入榜单第一顄1�7
            pagenum=int(loadurl(list_url).get('pagenum'))
            for page in range(pagenum):
                page+=1#当前页从1计数
                current_url=LIST % (DICT.get(channel), page)
                lists=loadurl(current_url).get('lists')
                for episode in lists:
                    data={
                            'title':episode.get('name'),
                            'image':episode.get('pic'),
                            'category':episode.get('cate'),
                            'channel':channel,
                            'source':SOURCE
                        }
                    Scheduler.schedule(
                                       AlbumCrawler.type,
                                       episode.get('mid'),
                                       data,
                                       reset=True
                                       )

class AlbumCrawler(Crawler):
    type='video.fengxing.album'
     
    
    #可被解析的url规范＄1�7
    '''
    匹配格式＄1�7
    详情页：http://m.funshion.com/subject?mediaid=104723
    播放页：http://m.funshion.com/play?mediaid=1283             #电影
          http://m.funshion.com/play?mediaid=104723&number=1  #其它
    '''
    @staticmethod
    def extract_key(url):
        url=url.strip()
        pram=re.findall('^http://m.funshion.com/\w+\?mediaid=(\d+)',url)
        return pram[0] if pram else None
             
    def crawl(self):
        videos = []
        mid = self.key
        url = DETAIL % mid
        detail = loadurl(url)
        description = detail.get('plots')
        description = ''.join(description.split())
        if self.data.get('channel') == u'电影':
            dict_ = detail['pinfos']['mpurls']
            video = VideoItemModel({
                                    "title": self.data.get('title'),
                                    "url": MOVIE_PLAY % mid, #网页地址
                                    "image": self.data.get('image'),
                                    "description": description,
                                    "stream": [{
                                                 'url': dict_['tv'].get('url'),
                                                 'size': dict_['tv'].get('bits'),
                                                 'format': 'mp4'
                                                }]
                                    })   
            videos.append(video)
        else:
            try:
                sort = detail['pinfos'].get('sort')[0]    
                episodes = detail['pinfos']['content'][sort]['fsps']
            except:
                episodes = detail['pinfos']['fsps']

            for episode in episodes:
                plots = episode.get('plots')
                plots = ''.join(plots.split())                
                video = VideoItemModel({
                                     "title": episode.get('taskname'),
                                     "url": PLAY_URL % (mid,episode.get('number')), #网页地址
                                     "image": episode.get('picurl'),
                                     "description": plots,
                                     "stream": getstream(episode.get('mpurls'))
                                     })
                videos.append(video)           
        model = VideoSourceModel({
                                 "source": self.data.get('source'), 
                                 "source_id": mid, #源站ID
                                 "title": self.data["title"],
                                 "url": detail.get('shareurl'), #详情页的地址
                                 "image": self.data.get('image'), #图片url
                                 "categories": self.data.get('category'), #分类
                                 "channel": self.data.get('channel'), #频道
                                 "region": detail.get('country'), #地区
                                 "videos": videos, #视频专辑
                                 "pubtime": parse_date(detail.get('rinfo').split(' ')[0]), #上映时间
                                 "actors": detail.get('lactor'),
                                 "directors": detail.get('director'),
                                 "description": description,
                                 })
        #导出数据
        export(model)
        self.data['to_album_id'] = model['to_album_id']
              
                
                
def loadurl(url):
    page = urllib.urlopen(url)
    data = page.read()
    data = json.loads(data).get('data')
    return  data
                     
def getstream(dic):
    d = {}
    stream = []
    for v in dic.values():
        d['url'] = v.get('url')
        d['size'] = v.get('bits')
        d['format'] = 'mp4'
        stream.append(d)
    return stream
 
if __name__=='__main__':
    #test
    ListCrawler(data = {'updated' : datetime.min}).crawl()  
    #test
    '''
    data={
          'title':"猫和老鼠四川牄1�7",
          'image':"http://img.funshion.com/pictures/198/495/3/1984953_s.jpg",
          'category':['类型',' 搞笑', '冒险','亲子'],
          'channel':'动漫'
         }
         
    AlbumCrawler(key="95356",data=data).crawl()
    '''