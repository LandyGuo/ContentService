#coding=utf8
import re, requests
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.novel import NovelSourceModel
from contentservice.utils.novelutil import extract_chapter_number
from common import save_txt

class NovelListCrawler(Crawler):

    type = "novel.luoqiu.novellist"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(NovelListCrawler.type, "", data = {"last_updated" : datetime.min}, priority = Priority.High, interval = 3600)

    def crawl(self):
        min_time = self.data['last_updated']
        max_time = None
        time = None

        for header_url in self.get_header_urls():
            try:
                content = download(header_url)
            except:
                self.logger.warning("Download failed - %s" % header_url)
                continue

            hxs = HtmlXPathSelector(text = content)
            for s in hxs.select("//ul[@class='articlelist']/li"):
                try:
                    url = s.select("div[1]/a/@href").extract()[0]
                    source_id = re.match(".+/(\d+)\.html", url).group(1)

                    name = s.select("div[1]/a/text()").extract()[0].strip()
                    author = s.select("div[2]/a/text()").extract()[0].strip()
                    last_chapter = s.select("div[3]/a/text()").extract()[0].strip()
                    words = s.select("div[4]/text()").extract()[0]
                    words = int(re.match("(^\d+)K", words).group(1)) * 1000

                    visits = int(s.select("div[5]/text()").extract()[0])

                    time = s.select("div[6]/text()").extract()[0]
                    time = datetime.strptime(time, "%y-%m-%d")
                    if not max_time:
                        max_time = time
                    if time < min_time:
                        break

                    novel_status = s.select("div[7]/text()").extract()[0]

                    completed = False if novel_status == u'连载中' else True
                except:
                    continue

                data = {
                            "source_id" : source_id,
                            "time" : time,
                            'title' : name,
                            'visits' : visits,
                            'author' : author,
                            'words' : words,
                            'last_chapter' : last_chapter,
                            'completed' : completed,
                        }

                lastdata = Scheduler.get_data(NovelCrawler.type, source_id)
                lasttime = lastdata.get("time", datetime.min) if lastdata else datetime.min
                Scheduler.schedule(type = NovelCrawler.type, key = source_id, data = data, reset = data['time'] >= lasttime)

            if time and time < min_time:
                break

        if max_time:
            self.data['last_updated'] = max_time


    def get_header_urls(self):

        _DEFAULT_PAGE_COUNT = 2600

        def _get_header_page_count():
            try:
                url = "http://www.luoqiu.com/gengxin/1.html"
                hxs = HtmlXPathSelector(text = download(url))
                text = hxs.select("//em[@id='pagestates']/text()").extract()[0]
                return int(re.findall("\(1/(\d+)\)", text)[0])
            except:
                return _DEFAULT_PAGE_COUNT


        baseurl = "http://www.luoqiu.com/gengxin/"
        page_count = _get_header_page_count()
        urls = []
        for i in range(1, page_count):
            url = baseurl + str(i) + ".html"
            urls.append(url)
        return urls


class NovelCrawler(Crawler):

    type = "novel.luoqiu.novel"

    def crawl(self):
        source_id = int(self.data['source_id'])

        url = "http://www.luoqiu.com/book/%s/%s.html" % (source_id / 1000, source_id)
        hxs = HtmlXPathSelector(text = download(url))

        descriptions = hxs.select("//ul[@class='block-intro']/text()").extract()
        description = "\n".join(descriptions).strip()

        image = hxs.select("//div[@class='bookcover']/a/img/@src").extract()[0]
        if image.find("nocover") != -1:
            image = ""

        try:
            category = hxs.select("//div[@class='bookinfo']/a[@class='type']/text()").extract()[0]
        except:
            category = ""
        try:
            s = hxs.select("//div[@class='score']")
            score = float(s.select(".//span[@id='shi']/text()").extract()[0]) + float(s.select(".//span[@id='ge']/text()").extract()[0]) * 0.1
        except:
            score = 0

        novel = NovelSourceModel({
                            "source" : self.data['source'],
                            "source_id" : source_id,
                            "url" : url,
                            "description" : description,
                            "category" : category,
                            'image' : image,
                            'score' : score,
                            'title' : self.data['title'],
                            'time' : self.data.get('time'),
                            'visits' : self.data.get('visits'),
                            'author' : self.data.get('author'),
                            'words' : self.data.get('words'),
                            'completed' : self.data.get('completed'),
                            })

        #Crawl index
        baseurl = "http://www.luoqiu.com/html/%s/%s/" % (source_id / 1000, source_id)
        url = baseurl + "index.html"

        hxs = HtmlXPathSelector(text = download(url))

        chapters = []
        last_season = 0
        for s in hxs.select("//div[@class='booklist clearfix']/span/a"):
            title = s.select("text()").extract()[0].strip()
            url = baseurl + s.select("@href").extract()[0].strip()
            season, chapter = extract_chapter_number(title)
            if season:
                last_season = season
            elif chapter:
                season = last_season

            Scheduler.schedule(type = ChapterCrawler.type, key = "%s#%s" % (source_id, len(chapters)),\
                           data = {"url" : url}, priority = Priority.Low)

            chapters.append({
                         "title" : title,
                         "url" : url,
                         "price" : 0.0,
                         })

        novel['chapters'] = chapters

        export(novel)


class ChapterCrawler(Crawler):

    type = "novel.luoqiu.chapter"

    def crawl(self):
        source_id, index = self.key.split("#")
        hxs = HtmlXPathSelector(text = download(self.data['url']))
        lines = hxs.select("//div[@id='content']/.//text()").extract()
        content = "\n".join(lines).strip()

        if content:
            save_txt(self.data['source'], source_id, index, content)


def download(url):
    resp = requests.get(url)
    resp.encoding = 'gbk'
    resp.raise_for_status()
    return resp.text


if __name__ == "__main__":

    data =  {
        "title" : u"莽荒纪",
        "completed" : False,
        "author" : u"我吃西红柿",
        "words" : 2297391,
        "visits" : 17823498,
        "time" : datetime.utcnow(),
        "source_id" : "73800",
        }
    NovelCrawler(key = "73800", data = data).crawl()


#     data = {
#         "url" : "http://www.luoqiu.com/html/75/75777/11047753.html",
#         "index" : 19,
#         "novel" : u"和表姐同居的日子",
#         }
#
#     ChapterCrawler(data = data).crawl()

