#coding=utf8

import urllib,json
from datetime import datetime
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoSourceModel, VideoItemModel
from contentservice.utils.datetimeutil import parse_date


HOT_LIST = "http://v.ifeng.com/appData/subChannelList/100409-0_androidPhone_%s.js"

CHANNEL = u"热点"
SOURCE = "fenghuang"


class ListCrawler(Crawler):
    type = 'video.fenghuang.list'
    
    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(
                           ListCrawler.type, #爬虫类型
                           key = "", #该类型只有一个实例,key设""
                           priority = conf.get('priority', Priority.High), #优先级为高
                           data = {'updated' : datetime.min}, #附加数据为上次爬取到的最新视频的更新时间
                           interval = conf.get('interval', 3600) #循环抓取间隔为1小时
                           )
    def crawl(self):
        page = 1
        while(True):
            url = HOT_LIST % page
            video_list = loadurl(url)
            if video_list == None:
                break
            else:
                for videoinfo in video_list:
                    video = videoinfo['video'][0]
                    video['source'] = SOURCE
                    Scheduler.schedule(
                                       AlbumCrawler.type,
                                       video.get('id'),
                                       data = video
                                       )   
                page+=1               
                    
        
class AlbumCrawler(Crawler):
    
    type = 'video.fenghuang.album' 
    
    '''
    凤凰网的所有内容均由榜单爬虫获得，没有详情页，因此在专辑爬虫内不能解析
    '''
    @staticmethod
    def extract_key(url):
        return None
    
    def crawl(self): 
        timestr = self.data.get('videoLength','00:00')
        duration = gettime(timestr)
        videos = []
        video = VideoItemModel({
                                "title": self.data.get('title'),
                                "url": self.data.get('videoURLMid'), #网页地址
                                "image": self.data.get('imgURL'),
                                "description": self.data.get('desc'),
                                "stream": [{
                                           "url": self.data.get('videoURLMid'), #视频文件播放地址
                                           "size": self.data.get('videoSizeMid'),
                                           "format": "mp4", #视频格式(协议)
                                           "duration": duration
                                          }],
                                "stream_low":[{
                                         "url": self.data.get('videoURLLow'), 
                                         "size": self.data.get('videoSizeLow'),
                                         "format": "mp4",
                                         "duration": duration
                                        }],
                                "stream_high":[{
                                         "url": self.data.get('videoURLHigh'),
                                         "size": self.data.get('videoSizeHigh'),
                                         "format": "mp4", 
                                         "duration": duration
                                        }]
                            })
        videos.append(video)   
        model = VideoSourceModel({
                                 "source": self.data.get('source'),
                                 "source_id": self.data.get('id'), #源站ID
                                 "title": self.data.get("title"),
                                 "url": self.data.get('shareurl'), #详情页的地址
                                 "image": self.data.get('imgURL'), #图片url
                                 "channel": CHANNEL, #频道
                                 "videos": videos, #视频专辑
                                 "pubtime": parse_date(self.data.get('videoPublishTime')), #上映时间
                                 "description": self.data.get('desc'),
                                 })
        #导出数据
        export(model)
        self.data['to_album_id'] = model['to_album_id']
 
        
        
def loadurl(url):
    page = urllib.urlopen(url)
    data = page.read()
    try:
        ddata = json.loads(data)
    except ValueError:
        return None
    return ddata['channelList'] 


def gettime(timestr):#str="xx:xx"
    time = timestr.split(':')
    try:
        minute = int(time[0])
        second = int(time[1])
    except :
        minute = 0
        second = 0
    return 60*minute+second
    


if __name__=='__main__':
    #test
    #ListCrawler(data = {'updated' : datetime.min}).crawl()  
    #json包中的数据样式
    data={
          'id': "785540",
          'statisticID': "100376-100409-100413",
          'GUID': "0157bb5c-e673-44dc-b760-8eb99b64593f",
          'title': "触动地方利益",
          'longTitle': "专家：“单独”二胎新政策触动地方利益",
          'imgURL': "http://y2.ifengimg.com/a/2013_47/4caaf799388d658.png",
          'videoURLHigh': "http://video19.ifeng.com/video07/2013/11/17/292682-102-007-1539.mp4",
          'videoURLMid': "http://3gs.ifeng.com/userfiles/video01//2013/11/17/292682-280-068-1539.mp4",
          'videoURLLow': "http://3gs.ifeng.com/userfiles/video01//2013/11/17/292682-280-068-1539.mp4",
          'videoLength': "",
          'videoPublishTime': "2013-11-17 15:34:00",
          'shareURL': "",
          'playTimes': "",
          'audioURL': "http://3gs.ifeng.com/userfiles/audio01//2013/11/17/292682-535-066-1539.mp3",
          'videoSizeHigh': "10990",
          'videoSizeMid': "6540",
          'videoSizeLow': "6540",
          'collect': "",
          'lastPlayedTime': "",
          'CP': "凤凰卫视",
          'type': "video",
          'GeneralTitle': "[解读全会] 单独可生二胎 准生还要敢生",
          'desc': "",
          'largeImgURL': "http://d.ifengimg.com/w480_h360/y0.ifengimg.com/pmop/storage_img/2013/11/17/0307ab21-6210-4488-ba89-4e26e2f63e7740.jpg",
          'smallImgURL': "http://y2.ifengimg.com/a/2013_47/4caaf799388d658.png"
          }
    AlbumCrawler(key="768471",data=data).crawl()