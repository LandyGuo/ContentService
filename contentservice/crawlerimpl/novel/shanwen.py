#coding=utf8
import re, requests
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.novel import NovelSourceModel
from contentservice.utils.novelutil import extract_chapter_number
from common import save_txt

class NovelListCrawler(Crawler):

    type = "novel.shanwen.novellist"

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
                return

            hxs = HtmlXPathSelector(text = content)
            for s in hxs.select("//td[@id='centerTcolumn']/table[@class='grid']/tr"):
                try:
                    url = s.select("td[1]/a/@href").extract()[0]
                    source_id = re.match(".+/(\d+)\.htm", url).group(1)

                    name = s.select("td[1]/a/.//text()").extract()[0].strip()
                    last_chapter = s.select("td[2]/a/text()").extract()[0].strip()
                    author = s.select("td[3]/text()").extract()[0].strip()
                    words = s.select("td[4]/text()").extract()[0]
                    words = int(re.match("(^\d+)", words).group(1)) * 1000

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
                            'title' : name,
                            'author' : author,
                            'words' : words,
                            'last_chapter' : last_chapter,
                            'completed' : completed,
                        }

                lastdata = Scheduler.get_data(NovelCrawler.type, source_id)
                lasttime = lastdata.get("time", datetime.min) if lastdata else datetime.min
                Scheduler.schedule(type = NovelCrawler.type, key = source_id, data = data, reset = data['time'] > lasttime)

            if time and time < min_time:
                break

        if max_time:
            self.data['last_updated'] = max_time


    def get_header_urls(self):

        _DEFAULT_PAGE_COUNT = 400

        def _get_header_page_count():
            try:
                url = "http://www.shanwen.com/swtoplastupdate/0/1.htm"
                hxs = HtmlXPathSelector(text = download(url))
                text = hxs.select("//td[@id='centerTcolumn']/table[2]/tr/td/table/tr/td[1]/text()").extract()[0]
                return int(re.findall("\(1/(\d+)\)", text)[0])
            except:
                return _DEFAULT_PAGE_COUNT


        baseurl = "http://www.shanwen.com/swtoplastupdate/0/"
        page_count = _get_header_page_count()
        urls = []
        for i in range(1, page_count):
            url = baseurl + str(i) + ".htm"
            urls.append(url)
        return urls


class NovelCrawler(Crawler):

    type = "novel.shanwen.novel"

    def crawl(self):
        source_id = int(self.data['source_id'])

        url = "http://www.shanwen.com/swinfo/%s/%s.htm" % (source_id / 1000, source_id)
        hxs = HtmlXPathSelector(text = download(url))

        image = hxs.select("//div[@id='content']/table[1]/tr[1]/td[1]/table[2]/tr[1]/td[2]/a/img/@src").extract()
        image = image[0] if image else ''

        descriptions = hxs.select("//div[@id='content']/table[1]/tr[1]/td[1]/table[2]/tr[1]/td[1]/div[1]/font[1]/text()").extract()
        description = "\n".join(descriptions)

        category = ""
        for text in hxs.select("//div[@id='content']/.//div[@class='blockTitle']/table[2]/tr/td/.//text()").extract():
            m = re.match(u"类别：\s+(.+)", text)
            if m:
                category = m.group(1)
                break

        novel = NovelSourceModel({
                            "source" : self.data['source'],
                            "source_id" : source_id,
                            "url" : url,
                            "description" : description,
                            "category" : category,
                            'image' : image,
                            'time' : self.data.get('time'),
                            'title' : self.data['title'],
                            'author' : self.data.get('author'),
                            'words' : self.data.get('words'),
                            'completed' : self.data.get('completed'),
                            })

        #Crawl index
        baseurl = "http://read.shanwen.com/%s/%s/" % (source_id / 1000, source_id)
        url = baseurl + "index.html"

        hxs = HtmlXPathSelector(text = download(url))

        s = hxs.select("//div[@class='bookdetail']/table")
        links = s.select(".//a/@href").extract()
        names = s.select(".//a/text()").extract()
        chapters = []
        if links and names and len(links) == len(names):
            last_season = 0
            for i in range(0, len(links)):
                name = names[i].strip()
                url = baseurl + links[i]
                season, chapter = extract_chapter_number(name)
                if season:
                    last_season = season
                elif chapter:
                    season = last_season

                Scheduler.schedule(type = ChapterCrawler.type, key = "%s#%s" % (source_id, len(chapters)), \
                               data = {"url" : url}, priority = Priority.Low)

                chapters.append({
                                 "title" : name,
                                 "url" : url,
                                 "price" : 0.0,
                                 })

        novel['chapters'] = chapters
        export(novel)


class ChapterCrawler(Crawler):

    type = "novel.shanwen.chapter"

    def crawl(self):
        source_id, index = self.key.split("#")

        url = self.data['url']
        hxs = HtmlXPathSelector(text = download(url))
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
        "title" : u"金玉瞳",
        "completed" : False,
        "author" : u"喜欢雨中行",
        "words" : 2502000,
        "time" : datetime.utcnow(),
        "source_id" : "22157",
        }
    NovelCrawler(data = data).crawl()


    data = {
        "url" : "http://read.shanwen.com/22/22157/3652608.html",
        "index" : 15,
        "novel" : u"金玉瞳",
        }

    ChapterCrawler(data = data).crawl()

