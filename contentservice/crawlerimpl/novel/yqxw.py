#coding=utf8
import re, requests
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.novel import NovelSourceModel
from contentservice.utils.novelutil import extract_chapter_number
from common import save_txt

class NovelListCrawler(Crawler):

    type = "novel.yqxw.novellist"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(NovelListCrawler.type, "", data = {"last_updated" : datetime.min}, priority = Priority.High, interval = 86400)

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
            for s in hxs.select("//div[@id='content']/table/tr"):
                try:
                    url = s.select("td[1]/a/@href").extract()[0]
                    source_id = re.match(".+/(\d+)/index\.html", url).group(1)

                    title = s.select("td[1]/a/text()").extract()[0].strip()
                    author = s.select("td[1]/text()").extract()[1].strip()
                    author = re.match(".+/(.+)", author).group(1)

                    last_chapter = s.select("td[2]/a/text()").extract()[0].strip()

                    words = s.select("td[4]/text()").extract()[0]
                    words = int(re.match("(^\d+)", words).group(1))

                    time = s.select("td[5]/text()").extract()[0]
                    time = datetime.strptime(time, "%y-%m-%d")
                    if not max_time:
                        max_time = time
                    if time < min_time:
                        break

                    novel_status = s.select("td[6]/text()").extract()[0]
                    completed = False if novel_status == u'连载' else True
                except:
                    continue

                data = {
                            "source_id" : source_id,
                            "time" : time,
                            'title' : title,
                            'author' : author,
                            'words' : words,
                            'completed' : completed,
                            'last_chapter' : last_chapter,
                        }

                lastdata = Scheduler.get_data(NovelCrawler.type, source_id)
                lasttime = lastdata.get("time", datetime.min) if lastdata else datetime.min
                Scheduler.schedule(type = NovelCrawler.type, key = source_id, data = data, reset = data['time'] > lasttime)

            if time and time < min_time:
                break

        if max_time:
            self.data['last_updated'] = max_time


    def get_header_urls(self):

        _DEFAULT_PAGE_COUNT = 1070

        def _get_header_page_count():
            try:
                url = "http://www.yqxw.net/yqxwtoplastupdate/0/1.htm"
                hxs = HtmlXPathSelector(text = download(url))
                text = hxs.select("//em[@id='pagestates']/text()").extract()[0]
                return int(re.findall("\(1/(\d+)\)", text)[0])
            except:
                return _DEFAULT_PAGE_COUNT


        baseurl = "http://www.yqxw.net/yqxwtoplastupdate/0/"
        page_count = _get_header_page_count()
        urls = []
        for i in range(1, page_count):
            url = baseurl + str(i) + ".htm"
            urls.append(url)
        return urls


class NovelCrawler(Crawler):

    type = "novel.yqxw.novel"

    def crawl(self):
        source_id = int(self.data['source_id'])
        base_url = "http://www.yqxw.net/files/article/html/%s/%s/" % (source_id / 1000, source_id)
        index_url = base_url + "index.html"

        hxs = HtmlXPathSelector(text = download(index_url))

        description = hxs.select("//div[@class='introtxt']/text()").extract()[0]

        novel = NovelSourceModel({
                            "source" : self.data['source'],
                            "source_id" : source_id,
                            "url" : index_url,
                            "description" : description,
                            'title' : self.data['title'],
                            'time' : self.data.get('time'),
                            'author' : self.data.get('author'),
                            'words' : self.data.get('words'),
                            'completed' : self.data.get('completed'),
                            'last_chapter' : self.data.get('last_chapter'),
                            })

        #Crawl index
        chapters = []
        last_season = 0
        for s in hxs.select("//div[@class='contents_body']/div[@class='contents_body_nr']/div[@class='contents_body_nr_02']/.//li"):
            try:
                title = s.select("a/text()").extract()[0].strip()
                chapter_url = base_url + s.select("a/@href").extract()[0]
            except Exception:
                continue
            season, chapter = extract_chapter_number(title)
            if season:
                last_season = season
            elif chapter:
                season = last_season

            Scheduler.schedule(type = ChapterCrawler.type, key = "%s#%s" % (source_id, len(chapters)), \
                           data = {"url" : chapter_url}, priority = Priority.Low)

            chapters.append({
                             "url" : chapter_url,
                             "title" : title,
                             "price" : 0.0,
                             })

        novel['chapters'] = chapters
        export(novel)


class ChapterCrawler(Crawler):

    type = "novel.yqxw.chapter"

    def crawl(self):
        source_id, index = self.key.split("#")

        url = self.data['url']
        hxs = HtmlXPathSelector(text = download(url))
        lines = hxs.select("//div[@class='readpage_body']/div[@class='readpage_body_nr']/div[@class='readpage_body_nr_02']/div[1]/text()").extract()
        content = "\n".join([line.strip() for line in lines])
        if content:
            save_txt(self.data['source'], source_id, index, content)

def download(url):
    resp = requests.get(url)
    resp.encoding = 'gbk'
    resp.raise_for_status()
    return resp.text

if __name__ == "__main__":
    data =  {
        "title" : u"梅花烙",
        "completed" : False,
        "author" : u"季荭",
        "words" : 90238,
        "time" : datetime.utcnow(),
        "source_id" : "17171",
        }
    NovelCrawler(data = data).crawl()


    data = {
        "url" : "http://www.yqxw.net/files/article/html/17/17171/196623.html",
        "index" : 10,
        "novel" : u"梅花烙",
        }

    ChapterCrawler(data = data).crawl()


