#coding=utf8
import re, requests, urlparse, urllib, urllib2, HTMLParser, json
from scrapy.selector import HtmlXPathSelector
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.novel import NovelRankModel, NovelSourceModel
from contentservice.utils import get_exception_info
from common import save_txt

'''
http://m.baidu.com/book/data/cates?pn=1
http://m.baidu.com/book/data/cate?pn=2&cateid=3
http://m.baidu.com/book/jump/cate?gid=984715390
'''

RANK_TYPE_MAP = {
              u"全部" : ("search.all", u"总榜"),    #origin_title -> type, title
              u"玄幻奇幻" : ("search.xuanhuan", u"玄幻"),
              u"言情" : ("search.yanqing", u"言情"),
              u"仙侠" : ("search.wuxia", u"武侠"),
              u"悬疑" : ("search.xuanyi", u"悬疑"),
#              u"历史军事" : "search.lishi",
#              u"完结" : "search.wanjie",
#              u"免费" : "search.mianfei",
              }
_HTML_PARSER = HTMLParser.HTMLParser()

class TopCrawler(Crawler):

    type = "novel.baidu.top"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(TopCrawler.type, priority = Priority.High, interval = 86400)

    def crawl(self):
        hxs = load_html(urlparse.urljoin("http://top.baidu.com", "category?c=10"))
        for s in hxs.select("//div[@id='flist']/div/ul/li"):
            try:
                title = s.select("a/text()").extract()[0].strip()
                href = s.select("a/@href").extract()[0]
                if href.find("buzz?") == -1:
                    continue
                url = urlparse.urljoin("http://top.baidu.com", href)
                if RANK_TYPE_MAP.has_key(title):
                    rank_title, rank_type = RANK_TYPE_MAP[title]
                    self.crawl_rank(url, rank_title, rank_type)
            except:
                self.logger.warning(get_exception_info())


    def crawl_rank(self, rank_url, rank_type, rank_title):
        hxs = load_html(rank_url)
        novels = []
        for s in hxs.select("//div[@id='main']/div[@class='mainBody']/.//td[@class='keyword']"):
            title = s.select("a/text()").extract()[0].strip()
            if not title:
                continue
            href = s.select("a/@href").extract()[0].strip()
            if href.find("detail?") == -1:
                continue
            url = urlparse.urljoin("http://top.baidu.com", href)
            novels.append(title)
            Scheduler.schedule(type = NovelCrawler.type, key = title)

        export(NovelRankModel({
                        "source" : self.data['source'],
                        "title" : rank_title,
                        "type" : rank_type,
                        "novels" : novels,
                        }))


class CategoryListCrawler(Crawler):

    type = "novel.baidu.categorylist"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(CategoryListCrawler.type, priority = Priority.High, interval = 86400)

    def crawl(self):
        url = "http://m.baidu.com/book/data/cates"
        data = json.loads(urllib.urlopen(url).read())
        for cat in data['result']['cates']:
            Scheduler.schedule(CategoryCrawler.type, key = str(cat['cateid']), priority = Priority.High, interval = 86400, timeout = 86400)


class CategoryCrawler(Crawler):
    type = "novel.baidu.category"

    def crawl(self):
        cateid = self.key
        max_pn = 30000
        pn = 1
        while pn < max_pn:
            try:
                url = "http://m.baidu.com/book/data/cate?pn=%s&cateid=%s" % (pn ,cateid)
                data = json.loads(urllib.urlopen(url).read())
                if data.get('errno') == 702:
                    self.logger.info("pn=%s, data=%s" % (pn, data))
                    break

                catename = data['result']['catename']
                for item in data['result']['cate']:
                    data = {
                              "title" : item['title'],
                              "gid" : item['gid'],
                              "src" : item['listurl'],
                              "last_chapter" : item['lastChapter'].get('text'),
                              "category" : catename,
                              }
                    key = item['gid']

                    olddata = Scheduler.get_data(NovelCrawler.type, key)
                    reset = olddata and olddata.get('last_chapter') != data['last_chapter'] and olddata.get('gid') == item['gid']

                    Scheduler.schedule(NovelCrawler.type, key, data = data, reset = reset)
            except:
                self.logger.warning(get_exception_info())

            pn += 1


class NovelCrawler(Crawler):

    type = "novel.baidu.novel"

    def crawl(self):
        gid = self.key
        src = self.data.get('src') if self.data else None
        category = self.data.get('category') if self.data else None

        url = "http://m.baidu.com/book/jump/cate?gid=%s" % gid
        if not src:
            resp = urllib.urlopen(url)
            src = urllib2.unquote(re.findall('[&\?]src=([^&]+)',resp.url)[0])

        params = {
                  "srd" : 1,
                  "appui" : 'alaxs',
                  'ajax' : 1,
                  'alalog' : 1,
                  'gid' : gid,
                  'dir' : 1,
                  'ref' : 'book_iphone',
                  'src' : src,
                  }

        ajax_url = "http://m.baidu.com/tc?" + urllib.urlencode(params)

        resp = urllib.urlopen(ajax_url)
        data = json.loads(_HTML_PARSER.unescape(unicode(resp.read(), 'utf8')))
        if data["status"] != 1:
            raise Exception("Invalid return status - %s" % data)

        data = data["data"]
        chapters = []
        for item in data["group"]:
            chapter_src = item["href"]
            chapter_title = item["text"]
            chapter_cid = item.get("cid", "")

            chapter_params = {
                              "srd" : 1,
                              "appui" : 'alaxs',
                              "ajax" : 1,
                              "gid" : gid,
                              "alals" : 1,
                              "preNum" : 1,
                              "preLoad" : "true",
                              "src" : chapter_src,
                              "cid" : chapter_cid,
                              }
            chapter_data_url = "http://m.baidu.com/tc?" + urllib.urlencode(chapter_params)
            chapter_url = "http://m.baidu.com/tc?appui=alaxs#!/zw/" + chapter_src

            index = len(chapters)
            Scheduler.schedule(ChapterCrawler.type,
                        key = "%s#%s" % (gid, index),
                        priority = Priority.Low,
                        data = {"url" : chapter_data_url})

            chapters.append({
                             "title" : chapter_title,
                             "url" : chapter_url,
                             "price" : 0.0,
                             })

        novel = NovelSourceModel({
                    "source" : self.data['source'],
                    "source_id" : gid,
                    "title" : data["title"],
                    "author" : data["author"],
                    "image" : filter_image(data.get("coverImage", "")),
                    "url" : url,
                    "chapters" : chapters,
                    "description" : data.get("summary"),
                    "completed" : data["status"].find(u"连载") == -1,
                    'category' : category,
                    })
        export(novel)

class ChapterCrawler(Crawler):
    type = "novel.baidu.chapter"

    def crawl(self):
        source_id, index = self.key.split("#")

        resp = urllib.urlopen(self.data["url"])
        data= json.loads(_HTML_PARSER.unescape(unicode(resp.read(), 'utf8')))
        if data["status"] != 1:
            raise Exception("Invalid return status - %s" % data)
        data = data["data"][0]
        content = data["content"]
        hxs = HtmlXPathSelector(text = content)
        content = "\n".join(hxs.select("//text()").extract())
        if content:
            save_txt(self.data['source'], source_id, index, content)

IMAGE_BLACKLIST = [
                   'nocover',
                   'default',
                   'noimg',
                   'nopic',
                   'http://images.zhulang.com/www/image/no_book.gif',
                   'http://www.xstxw.com/images/orange/images/coverpage_05.gif',
                   'http://imgw3gycw.3g.cn/UserUpload/BookPic/default/0.jpg',
                   'http://www.dzxsw.net/image/cover.jpg',
                   'http://image.cmfu.com/books/1.jpg',
                   'http://www.txtbbs.com/static/images/nopic.gif',
                   'http://www.lingdiankanshu.com/images/noimg.gif',
                   'http://img.17k.com/images/default_cover.jpg',
                   'http://staic.qefeng.com/cover/default.jpg',
                   'http://img.fbook.net/man/images/bookintro/fm.jpg',
                   'http://www.d3zw.com/images/noimg.gif',
                   ]

def search_novel(title):
    hxs = load_html_mobile(u"http://m.baidu.com/s?word=%s" % title)
    urls = hxs.select("//a[@class='ala_novel_rightbox_a']/@href").extract()
    if not urls:
        return
    url = urlparse.urljoin("http://m.baidu.com",urls[0])
    gid = re.findall('gid=(\d+)', url)[0]
    return gid

def filter_image(image):
    url = urllib.unquote(image).lower()
    for item in IMAGE_BLACKLIST:
        if url.find(item.lower()) != -1:
            return None
    return image

def load_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "gbk"
    return HtmlXPathSelector(text = resp.text)

def load_html_mobile(url):
    headers = {
               "User-Agent" : "Mozilla/5.0 (Linux; Android 4.1.1; Nexus 7 Build/JRO03D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166  Safari/535.19",
               }
    resp = requests.get(url, headers = headers)
    resp.raise_for_status()
    return HtmlXPathSelector(text = resp.text)

if __name__ == "__main__":
    #CategoryRankCrawler().crawl()
    #TopCrawler().crawl()
#    CategoryCrawler(key = 5).crawl()
    gid = search_novel(u"莽荒纪")
    NovelCrawler(key = gid, data = {}).crawl()
    #NovelCrawler(key = u'玥下自成汐', data = {'gid' : '1360190255'}).crawl()
