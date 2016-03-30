#coding=utf8
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
import requests, re
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.video import VideoSourceModel, VideoItemModel
from contentservice.utils.datetimeutil import parse_date
from contentservice.utils.text import split

class ListCrawler(Crawler):

    type = "video.zyqvod.list"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        Scheduler.schedule(ListCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 3600))

    def crawl(self):
        min_time = self.data.get('updated', datetime.min) if self.data else datetime.min
        max_time = None
        time = None

        page = 1
        while True:
            url = "http://zyqvod.com/?page=%s" % page
            hxs = load_html(url)

            for s in hxs.select("//table[@id='listTable']/tbody/tr"):
                try:
                    source_id = re.findall("id=(\d+)", s.select("td[1]/a/@href").extract()[0])[0]
                    title = clean_title(s.select("td[1]/.//text()").extract()[0])
                    category = s.select("td[2]/.//text()").extract()[0]
                    region = s.select("td[3]/.//text()").extract()[0]
                    completed = s.select("td[4]/.//text()").extract()[0] == u"完结"
                    time = s.select("td[5]/.//text()").extract()[0]
                    time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
                except:
                    continue

                if not max_time:
                    max_time = time
                if time < min_time:
                    break

                data = {
                            "title" : title,
                            "time" : time,
                            'category' : category,
                            'region' : region,
                            'completed' : completed,
                        }

                lastdata = Scheduler.get_data(AlbumCrawler.type, source_id)
                lasttime = lastdata.get("time", datetime.min) if lastdata else datetime.min
                Scheduler.schedule(type = AlbumCrawler.type, key = source_id, data = data, reset = data['time'] > lasttime)

            if time and time < min_time:
                break

            text = hxs.select("//div[@class='page_num']/text()").extract()[0]
            page_count = int(re.findall(u"\d+/(\d+)页", text)[0])
            if page >= page_count:
                break
            page += 1

        if max_time:
            if not self.data:
                self.data = {}
            self.data['updated'] = max_time


class AlbumCrawler(Crawler):
    type = "video.zyqvod.album"

    def crawl(self):
        album_url = "http://zyqvod.com/vod/index.asp?id=%s" % self.key
        hxs = load_html(album_url)

        urls = hxs.select("//div[@class='movievod']/li/input/@value").extract()
        videos = []
        for url in urls:
            m = re.match("qvod://(.+)", url)
            if not m:
                continue
            words = m.group(1).split("|")
            size = int(words[0])
            #md5 = words[1]
            title = words[2].split(".")[0]

            videos.append(VideoItemModel({
                            "title" : title,
                            "url" : url,
                            "stream" : [{"url" : url, "format" : "qvod", "size" : size}],
                            }))

        kv = {}
        for s in hxs.select("//div[@class='videoDetail']/p"):
            texts = s.select(".//text()").extract()
            if len(texts) >= 2:
                kv[texts[0].strip()] = texts[1].strip()

        description = "\n".join(hxs.select("//div[@class='movievod']/p[2]/text()").extract())
        try:
            image = hxs.select("//div[@class='videoPic']/img/@src").extract()[0]
        except:
            image = None

        model = VideoSourceModel({
                                 "source" : self.data['source'],
                                 "source_id" : self.key,
                                 "title" : self.data["title"],
                                 "time" : self.data.get('time'),
                                 "url" : album_url,
                                 "image" : image,
                                 "completed" : self.data.get('completed'),
                                 "categories" : [self.data.get('category')],
                                 "channel" : self.data.get('category'),
                                 "region" : self.data.get('region'),
                                 "videos" : videos,
                                 "actors" : split(kv.get(u'影片主演:')),
                                 "directors" : split(kv.get(u'影片导演:')),
                                 "pubtime" : parse_date(kv.get(u'上映年份:')),
                                 "description" : description,
                                 "completed" : not kv.get(u'连载状态:'),
                                 })
        export(model)


def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    return HtmlXPathSelector(text = resp.text)

def clean_title(title):
    title = re.sub("\[.+\]", "", title)
    title = re.sub("\(.+\)", "", title)
    return title.strip()

if __name__ == "__main__":
#    ListCrawler().crawl()

    data = {
            'title' : u'有报天天读',
            'category' : u'综艺',
            'completed' : False,
            'region' : u'港台',
            'time' : datetime(2013,9,9)
            }
    AlbumCrawler(key = "13323", data = data).crawl()
