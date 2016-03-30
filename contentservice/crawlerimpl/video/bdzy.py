#coding=utf8
'''
网站抓取代码示例 for http://bdzy.cc/

网站结构为一个更新榜单和每个视频的详情页组成，
分两个爬虫抓取，一个抓取更新榜单，另一个抓取单个视频详情
抓取榜单的爬虫会创建相应的详情爬虫，并传给相应的参数和数据

更新榜单地址: http://bdzy.cc/list/?0-1.html
视频详情地址: http://bdzy.cc/detail/?20808.html
'''         
import requests, re, HTMLParser 
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Scheduler, Priority, export
from contentservice.models.video import VideoSourceModel, VideoItemModel
from contentservice.utils.datetimeutil import parse_date
from contentservice.utils.text import split
from contentservice.utils import get_exception_info

'''
重要方法说明
Scheduler.schedule(type, key, priority, data, reset, interval, timeout)
    type - 爬虫任务的类型
    key - 爬虫任务在该类型中的唯一标识（type和key组合起来唯一标识所爬取的内容，key通常为源站id）
    priority - 任务优先级 High, Normal, Low
    data - 附加数据（用来持久化跟该爬虫实例相关的数据），附加数据每次运行完成会自动持久化
    reset - 是否强制重新抓取。默认不会重新抓取已经完成的任务
    interval - 任务循环运行的间隔时间，0为只运行一次，默认值为0
    timeout - 超时时间，超时会自动杀死任务

Crawler
爬虫基类，每类爬虫都需要继承这个类
方法:
    init(conf=None)  初始化（每次程序启动调用一次），用于创建起始爬虫任务
    crawl() 爬取代码的主函数
重要成员变量:
    self.key  该爬虫实例的key
    self.data 附加数据
    self.logger Logger

export(ContentModel)
导出爬取的数据，数据会自动做清理，映射，合并，最后存到mongodb
    ContentModel - 所有导出的数据结构需要继承此类, 结构定义在models/video.py，其中FIELDS定义了数据字段的名称和类型、默认值, FIELDS可从基类继承

'''

class ListCrawler(Crawler):

    '''
    爬取总榜单的内容，该视频榜单按照更新时间逆序，self.data保存上次爬取到的最新的时间（每次只需爬取新增的部分榜单）
    url format: http://bdzy.cc/list/?0-[page].html
    '''
    type = "video.bdzy.list" #爬虫类型，格式为 '[video|novel|music].[source].[name]'

    @staticmethod
    def init(conf=None):
        '''
        爬虫初始化，用于创建起始爬虫。
        '''
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
        min_time = self.data['updated'] #上次爬取到最新视频的更新时间, 为本次爬取的时间下界
        max_time = None #本次抓取的最新视频的时间

        page = 1
        while True:
            url = "http://bdzy.cc/list/?0-%s.html" % page
            hxs = load_html(url) #读取网页html, 返回一个HtmlXPathSelector

            time = None
            for s in hxs.select("//body/.//tr[@class='row']"): #用xpath解析html
                try:
                    href = s.select("td[1]/a/@href").extract()[0]
                    source_id = re.findall("(\d+)\.html", href)[0] #源站ID
                    title = clean_title(s.select("td[1]/.//text()").extract()[0])
                    region = s.select("td[2]/.//text()").extract()[0].replace(u"地区", u"")
                    category = s.select("td[3]/.//text()").extract()[0]
                    time = s.select("td[4]/.//text()").extract()[0]
                    time = datetime.strptime(time, "%Y-%m-%d")

                    if not max_time: #第一条是最新更新的
                        max_time = time
                    if time < min_time: #已经爬取到上次最新的数据
                        break

                    data = { #详情页爬虫任务的附加数据
                        "title" : title,
                        "time" : time,
                        "category" : category,
                        "region" : region,
                        }

                    #获取对应详情页爬虫的附加数据，用time字段判断该内容是否已经更新，需要重新抓取. 如果第一次创建，则数据为空
                    lastdata = Scheduler.get_data(AlbumCrawler.type, source_id)
                    lasttime = lastdata.get("time", datetime.min) if lastdata else datetime.min

                    #创建相应的专辑爬虫，爬取相应的详情页. key为源站id
                    Scheduler.schedule(
                                       AlbumCrawler.type,
                                       source_id,
                                       data,
                                       reset = data["time"] > lasttime #是否需要强制重新抓取
                                       )
                except:
                    self.logger.warning(get_exception_info()) #纪录错误信息并继续
                    continue

            if time and time < min_time: #已经爬取到上次最新的数据
                break

            #获取总页数
            text = hxs.select("//div[@class='pages']/span/text()").extract()[0]
            page_count = int(re.findall(u"\d+/(\d+)页", text)[0])

            #超过总页数
            if page >= page_count:
                break
            page += 1

        if max_time:
            self.data = {'updated' : max_time} #保存上次爬取到的最新的时间


class AlbumCrawler(Crawler):
    '''
    爬取专辑详情信息
    http://bdzy.cc/detail/?[id].html
    '''
    type = "video.bdzy.album"

    def crawl(self):
        #key为专辑源站ID
        album_id = self.key

        album_url = "http://bdzy.cc/detail/?%s.html" % album_id
        hxs = load_html(album_url)

        urls = hxs.select("//td[@class='bt']/.//li/input/@value").extract()
        videos = []
        for url in urls:
            m = re.match("bdhd://(.+)", url)
            if not m:
                continue
            words = m.group(1).split("|")
            size = int(words[0])
            #md5 = words[1]
            title = words[2].split(".")[0]

            #视频剧集
            video = VideoItemModel({
                            "title" : title,
                            "url" : url, #网页地址 (这里没有，所以采用播放地址)
                            "stream" : [
                                        {
                                         "url" : url, #视频文件播放地址
                                         "size" : size,
                                         "format" : "bdhd" #视频格式(协议)
                                        }],
                            })

            videos.append(video)

        kv = {}
        for s in hxs.select("/html/body/table[2]/tr[1]/td[2]/table/tr"):
            texts = s.select(".//text()").extract()
            if len(texts) >= 2:
                kv[texts[0].strip()] = texts[1].strip()

        description = "\n".join(hxs.select("//div[@class='intro']/.//text()").extract())

        try:
            image = hxs.select("/html/body/table[2]/tr[1]/td[1]/img/@src").extract()[0]
        except:
            image = None

        #视频导出的数据模型
        model = VideoSourceModel({
                                 "source" : self.data['source'], #视频源
                                 "source_id" : album_id, #源站ID
                                 "title" : self.data["title"],
                                 "url" : album_url, #网页地址
                                 "image" : image, #图片url
                                 "time" : self.data.get('time'), #源站更新时间
                                 "categories" : [self.data.get('category')], #分类
                                 "channel" : self.data.get('category'), #频道
                                 "region" : self.data.get('region'), #地区
                                 "videos" : videos, #视频专辑数组
                                 "pubtime" : parse_date(kv.get(u"上映日期：")), #上映时间
                                 "actors" : split(kv.get(u"影片演员：")),
                                 "completed" : kv.get(u"影片状态：", "").find(u"连载") == -1, #是否完结
                                 "description" : description,
                                 })
        #导出数据
        export(model)

def clean_title(title):
    title = re.sub("\[.+\]", "", title)
    title = re.sub("\(.+\)", "", title)
    return title.strip()

def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "gbk"
    data = HTMLParser.HTMLParser().unescape(resp.text)
    return HtmlXPathSelector(text = data)

if __name__ == "__main__":
    '''
    Test Code Sample
    该测试方法未启动爬虫调度器，用于在本地测试单个爬虫的功能
    抓取的数据保存到mongodb
        - db: content_video
        - collection: video.source
    '''

    #test ListCrawler
    #ListCrawler(data = {'updated' : datetime.min}).crawl()

    #test AlbumCrawler
    data = {
            'title' : u'真是了不起',
            'category' : u'韩国电视剧',
            'region' : u'韩国',
            'time' : datetime(2013,9,9)
            }
    AlbumCrawler(key = "18825", data = data).crawl()


