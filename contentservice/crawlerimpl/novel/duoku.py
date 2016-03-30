#coding=utf8
import re, requests, random, sys
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.novel import NovelSourceModel
from contentservice.utils import get_exception_info
from common import save_txt

SERVER = "http://xs.duoku.com"

RANKS_DEF = [
            {
             "params" : {
                         "rdtp" : 0,
                         "rktp" : 1,
                         "rkdt" : 1,
                         },
             "title" : u"最新",
             "type" : "new",
             "limit" : sys.maxint,
             }
            ]

class NovelListCrawler(Crawler):

    type = "novel.duoku.novellist"

    @staticmethod
    def init(conf=None):
        for rank_def in RANKS_DEF:
            Scheduler.schedule(NovelListCrawler.type, key = rank_def['type'], data = rank_def, priority = Priority.High, interval = 86400)

    def crawl(self):
        params = self.data['params']
        limit = self.data['limit']
        novels = []
        page = 1
        while len(novels) < limit:
            params['pg'] = page
            params["pageid"] = "V6ashytl"
            try:
                hxs = load_html(params)
                for s in hxs.select("//div[@class='dk_content']/p"):
                    category = s.select("a[1]/text()").extract()
                    category = category[0].strip() if category else ""
                    title = s.select("a[2]/text()").extract()[0].strip()
                    if not title:
                        continue
                    url = s.select("a[2]/@href").extract()[0]
                    source_id = re.findall("bkid=(\d+)", url)[0]

                    novels.append(title)
                    data = {"title" : title, "url" : url, "category" : category, "source_id" : source_id}
                    Scheduler.schedule(NovelCrawler.type, key = source_id, data = data) #interval?

                if s.select("//div[@class='dk_pager']").extract()[0].find(u"下页") == -1:
                    break
                page += 1
            except Exception:
                self.logger.warning(get_exception_info())


class NovelCrawler(Crawler):
    type = "novel.duoku.novel"

    def crawl(self):
        params = {
                  "pageid" : "Yixbon41",
                  "full" : 1,
                  "bkid" : self.data["source_id"]
                  }

        hxs = load_html(params)

        title = hxs.select("//div[@class='dk_content']/p/span/text()").extract()[0]
        completed = title.find(u"[完本]") != -1
        title = re.sub("\[.+\]", "", title).strip()
        image = hxs.select("//div[@class='dk_novel_recommend']/.//img/@src").extract()
        image = image[0] if image else ""

        try:
            author = hxs.select("//div[@class='dk_novel_recommend']/.//div[@class='dk_padding5']/p[1]/text()").extract()[0]
            author = re.findall(u"作者:(.+)", author)[0].strip()
        except:
            author = ""

        try:
            description = hxs.select("//div[@class='dk_novel_recommend']/.//div[@class='dk_padding5']/p[2]/text()").extract()[0]
            description = re.findall(u"简介:(.+)$", description)[0].strip()
        except:
            description = ""

        try:
            words = re.findall(u"字数:([\d\.]+)千",hxs.select("//div[@class='dk_content10']").extract()[0])[0]
            words = int(float(words) * 1000)
        except:
            words = 0

        chapters = []
        page = 1
        while True:
            params = {
                      "pageid" : "Ryf46cus",
                      "bkid" : self.data["source_id"],
                      "pg" : page,
                      }
            hxs = load_html(params)

            for s in hxs.select("//div[@class='dk_content']/p"):
                number = s.select("span/text()").extract()[0]
                number = re.findall("(\d+)", number)
                if not number:
                    continue

                chapter_title = s.select("a/text()").extract()[0].strip()
                chapter_url = s.select("a/@href").extract()[0].strip()
                chapter_index = len(chapters)
                texts = "".join(s.select("text()").extract())
                is_free = texts.find(u"免费") != -1
                chapters.append({
                                 "title" : chapter_title,
                                 "price" : 0.0 if is_free else 0.01,
                                 "url" : chapter_url,
                                 })
                if is_free:
                    key = "%s#%s" % (self.data["source_id"], chapter_index)
                    data = {
                            "url" : chapter_url,
                            }
                    Scheduler.schedule(ChapterCrawler.type, key = key, priority = Priority.Low, data = data)

            if s.select("//div[@class='dk_pager']").extract()[0].find(u"下页") == -1:
                break
            page += 1

        export(NovelSourceModel({
                           "source" : self.data['source'],
                           "source_id" : self.data["source_id"],
                           "title" : title,
                           "image" : image,
                           "url" : self.data.get("url"),
                           "category" : self.data.get("category"),
                           "author" : author,
                           "description" : description,
                           "words" : words,
                           "completed" : completed,
                           "chapters" : chapters,
                           }))
        if completed:
            self.recursive = False


class ChapterCrawler(Crawler):
    type = "novel.duoku.chapter"

    def crawl(self):
        source_id, index = self.key.split("#")
        r = requests.get(self.data["url"])
        r.raise_for_status()
        hxs = HtmlXPathSelector(text = r.text)
        content = "\n".join(hxs.select("//div[@class='dk_content10']/p/text()").extract())
        if content:
            save_txt(self.data['source'], source_id, index, content)

def load_html(params = {}):
    params = params.copy()
    params_default = {
              "R" : random.randint(0, 300), #Random, no meaning
              "uid" : "wiaui_1371280138_5888", #user id? random generated?
              "v" : 2, #排版模式, 默认2
              "netFlag" : "cmnet",
              "dkfrc" : 1, #?
              "rdtp" : 0, #0 - 综合, 1 - 男生, 2 - 女生, 3 - 畅销
              "rktp" : 1, #1 - 热销, 2 - 人气, 12 - 点击, 6 - 字数
              "rkdt" : 1,  #1 - daily rank, 2 - weekly rank, 3 - monthly rank
              "pageid" : "V6ashytl", #总目录 - 排行
              "pg" : 1, #page number
              }

    for k, v in params_default.iteritems():
        if not params.has_key(k):
            params[k] = v

    r = requests.get(SERVER, params = params)
    r.raise_for_status()
    hxs = HtmlXPathSelector(text = r.text)
    return hxs

if __name__ == "__main__":
    #NovelListCrawler(key = rankdef['type'], data = RANKS_DEF[0]).crawl()
    #NovelCrawler(data = {"source_id" : "201209240471842"}).crawl()
    ChapterCrawler(data = {
                           "url" : "http://xs.duoku.com/?R=198&pageid=Ycpj2bxl&bkid=201209240471842&v=2&crid=20&uid=wiaui_1371280138_5888&netFlag=cmnet&dkfrc=1&rdtp=0",
                           "index" : 19,
                           "novel" : u"穿越占尽帝王宠",
                           }).crawl()

