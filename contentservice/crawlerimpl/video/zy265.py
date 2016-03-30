#coding=utf8
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
import requests, re, urlparse, HTMLParser
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.video import VideoSourceModel, VideoItemModel
from contentservice.utils.datetimeutil import parse_date
from contentservice.utils.text import split

_HTML_PARSER = HTMLParser.HTMLParser()

class ListCrawler(Crawler):

    type = "video.zy265.list"

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
            url = "http://www.265zy.com/list/?0-%s.html" % page
            hxs = load_html(url)

            for s in hxs.select("//body/.//tr[@class='row']"):
                try:
                    href = s.select("td[1]/a/@href").extract()[0]
                    source_id = re.findall("(\d+)\.html", href)[0]
                    title = clean_title(s.select("td[1]/.//text()").extract()[0])
                    region = s.select("td[2]/.//text()").extract()[0].replace(u"地区", u"")
                    category = s.select("td[3]/.//text()").extract()[0]
                    time = s.select("td[4]/.//text()").extract()[0]
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
                        }

                lastdata = Scheduler.get_data(AlbumCrawler.type, source_id)
                lasttime = lastdata.get("time", datetime.min) if lastdata else datetime.min
                Scheduler.schedule(type = AlbumCrawler.type, key = source_id, data = data, reset = data['time'] > lasttime)

            if time and time < min_time:
                break

            text = hxs.select("//div[@class='pages']/span/text()").extract()[0]
            page_count = int(re.findall(u"\d+/(\d+)页", text)[0])
            if page >= 5:
                break
            page += 1

        if max_time:
            if not self.data:
                self.data = {}
            self.data['updated'] = max_time


class AlbumCrawler(Crawler):
    type = "video.zy265.album"

    def crawl(self):
        album_url = "http://www.265zy.com/detail/?%s.html" % self.key
        hxs = load_html(album_url)

        urls = hxs.select("//td[@class='bt']/.//input[@id='copy_yah']/@value").extract()
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
        for s in hxs.select("/html/body/table[2]/tr[1]/td[2]/table/tr"):
            texts = s.select(".//text()").extract()
            if len(texts) >= 2:
                kv[texts[0].strip()] = texts[1].strip()

        description = "\n".join(hxs.select("//div[@class='intro']/.//text()").extract())
        try:
            image = urlparse.urljoin("http://www.265zy.com/", hxs.select("//div[@class='img']/img/@src").extract()[0])
        except:
            image = None

        model = VideoSourceModel({
                                 "source" : self.data['source'],
                                 "source_id" : self.key,
                                 "title" : self.data["title"],
                                 "image" : image,
                                 "url" : album_url,
                                 "time" : self.data.get('time'),
                                 "categories" : [self.data.get('category')],
                                 "channel" : self.data.get('category'),
                                 "region" : self.data.get('region'),
                                 "videos" : videos,
                                 "actors" : split(kv.get(u"影片演员：")),
                                 "pubtime" : parse_date(kv.get(u"上映日期：")),
                                 "completed" : kv.get(u"影片状态：", "").find(u"连载") == -1,
                                 "description" : description,
                                 })
        export(model)


def clean_title(title):
    title = re.sub("\[.+\]", "", title)
    title = re.sub("\(.+\)", "", title)
    return title.strip()

def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "gbk"
    data = _HTML_PARSER.unescape(resp.text)
    return HtmlXPathSelector(text = data)

if __name__ == "__main__":
#    ListCrawler().crawl()

    data = {
            'title' : u'真是了不起',
            'category' : u'韩国电视剧',
            'region' : u'韩国',
            'time' : datetime(2013,9,9)
            }
    AlbumCrawler(key = "18825", data = data).crawl()
