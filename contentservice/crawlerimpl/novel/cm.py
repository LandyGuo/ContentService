#coding=utf8
import re, requests, time, urlparse
from datetime import datetime
from ftplib import FTP
from scrapy.selector import HtmlXPathSelector
from common import save_txt
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.novel import NovelCMRankModel, NovelCMNovelModel, NovelCMChapterModel, NovelSourceModel
from contentservice.utils import get_exception_info

FTP_HOST = "211.140.17.111"
FTP_USER = "haitun"
FTP_PASSWD = "Kahrp2km"

class DATCrawler(Crawler):

    type = "novel.cm.dat"

    @staticmethod
    def init(conf=None):
        data = {
                "last_ibook_meta" : "book/meta/i_book_meta_20131022172000_20131022172500_0.dat",
                "last_ibook_chapter" : "book/chapter/i_book_chapter_20131022164000_20131022171000_0.dat",
                "last_rank" : {
                    "download#weekrank" : "book/weekrank/a_book_weekrank_download_20131021_0.dat"
                },
                "last_abook_meta" : "book/meta/a_book_meta_20130930_1.dat",
                "last_abook_chapter" : "book/chapter/a_book_chapter_20130930_27.dat"
                }
        Scheduler.schedule(DATCrawler.type, data = data, priority = Priority.High, interval = 86400, timeout = 86400)

    def crawl(self):
        self.ftp = None
        self.crawl_rank()
        self.crawl_meta()
        self.crawl_chapter()
        if self.ftp:
            self.ftp.quit()

    def ftp_login(self):
        self.ftp = FTP(FTP_HOST)
        self.ftp.login(user = FTP_USER, passwd = FTP_PASSWD)


    def crawl_rank(self):
        rank_type = "download#weekrank"

        path = self.get_latest_rank_path(rank_type)
        if not self.data.get('last_rank'):
            self.data['last_rank'] = {}
        last_rank = self.data["last_rank"].get(rank_type)
        if last_rank and cmp_path(last_rank, path) != -1:
            return

        ids = []
        def process_row(row):
            ids.append(row[0])

        self.ftp_parse_dat(path, process_row)
        item = NovelCMRankModel({
                          "type" : rank_type,
                          "ids" : ids
                          })
        item.collection().update({"type" : item["type"]}, item, upsert = True)

        self.data["last_rank"][rank_type] = path

    def crawl_meta(self):
        paths = self.get_ibook_meta_paths()
        for path in paths:
            if self.data["last_ibook_meta"] and cmp_path(self.data["last_ibook_meta"], path) != -1:
                continue
            self.crawl_meta_dat(path)
            self.data["last_ibook_meta"] = path

        paths = self.get_abook_meta_paths()
        for path in paths:
            if self.data["last_abook_meta"] and cmp_path(self.data["last_abook_meta"], path) != -1:
                continue
            self.crawl_meta_dat(path)
            self.data["last_abook_meta"] = path

    def crawl_chapter(self):
        paths = self.get_ibook_chapter_paths()
        for path in paths:
            if self.data["last_ibook_chapter"] and cmp_path(self.data["last_ibook_chapter"], path) != -1:
                continue
            self.crawl_chapter_dat(path)
            self.data["last_ibook_chapter"] = path

        paths = self.get_abook_chapter_paths()
        for path in paths:
            if self.data["last_abook_chapter"] and cmp_path(self.data["last_abook_chapter"], path) != -1:
                continue
            self.crawl_chapter_dat(path)
            self.data["last_abook_chapter"] = path

    def crawl_meta_dat(self, path):

        def process_row(row):
            novel_id = row[1]
            item = NovelCMNovelModel({
                                      "novel_id" : novel_id,
                                      "title" : row[2],
                                      "author" : row[4].split(";")[0],
                                      "tags" : row[5].split(";"),
                                      "description" : row[8],
                                      "category" : row[11],
                                      "price" : row[14], #price in cent
                                      "status" : row[19], #0 - completed, 1 - In progress
                                      "publisher" : row[25],

                                      "c00" : row[0],
                                      "c03" : row[3],
                                      "c06" : row[6],
                                      "c07" : row[7],
                                      "c09" : row[9],
                                      "c10" : row[10],
                                      "c12" : row[12],
                                      "c13" : row[13],
                                      "c15" : row[15],
                                      "c16" : row[16],
                                      "c17" : row[17],
                                      "c18" : row[18],
                                      "c20" : row[20],
                                      "c21" : row[21],
                                      "c22" : row[22],
                                      "c23" : row[23],
                                      "c24" : row[24],
                                      "c26" : row[26],
                                      })
            if len(row) > 30:
                item["publish_type"] = row[28]
                item["c27"] = row[27]
                item["c29"] = row[29]
                item["c30"] = row[30]

            item.collection().update({"novel_id" : novel_id}, item, upsert = True)

        self.ftp_parse_dat(path, process_row)

    def crawl_chapter_dat(self, path):

        updated_novel_ids = set()

        def process_row(row):
            novel_id = row[1]
            chapter_id = row[2]
            item = NovelCMChapterModel({
                                      "novel_id" : novel_id,
                                      "chapter_id" : chapter_id,
                                      "index" : row[3],
                                      "title" : row[4],
                                      "path" : row[5],
                                      "words" : int(row[6]),
                                      "time" : datetime.strptime(row[7], "%Y%m%d%H%M%S"),
                                      "price" : int(row[8]),
                                      "season_id" : row[9],
                                      "season_title" : row[10],
                                      })

            item.collection().update({"novel_id" : novel_id, "chapter_id" : chapter_id}, item, upsert = True)
            updated_novel_ids.add(novel_id)

        self.ftp_parse_dat(path, process_row)

        for novel_id in updated_novel_ids:
            Scheduler.schedule(NovelCrawler.type, key = novel_id, reset = True)


    def get_latest_rank_path(self, type = "download#weekrank"):
        rank_type, rank_span = type.split("#")

        lines = self.ftp_list("book/%s" % rank_span)
        paths = []
        for line in lines:
            names = re.findall("a_book_%s_%s_\d+_\d+\.dat" % (rank_span, rank_type), line)
            if names:
                paths.append(names[0])

        if paths:
            paths = sorted(paths, cmp_path)
            return "book/%s/%s" % (rank_span, paths[-1])
        else:
            return None

    def get_ibook_meta_paths(self):
        lines = self.ftp_list("book/meta")
        paths = []
        for line in lines:
            names = re.findall("i_book_meta_\d+_\d+_\d+\.dat", line)
            if names:
                paths.append("book/meta/" + names[0])
        return sorted(paths, cmp_path)

    def get_ibook_chapter_paths(self):
        lines = self.ftp_list("book/chapter")
        paths = []
        for line in lines:
            names = re.findall("i_book_chapter_\d+_\d+_\d+\.dat", line)
            if names:
                paths.append("book/chapter/" + names[0])
        return sorted(paths, cmp_path)

    def get_abook_meta_paths(self):
        lines = self.ftp_list("book/meta")
        paths = []
        for line in lines:
            names = re.findall("a_book_meta_\d+_\d+\.dat", line)
            if names:
                paths.append("book/meta/" + names[0])
        return sorted(paths, cmp_path)

    def get_abook_chapter_paths(self):
        lines = self.ftp_list("book/chapter")
        paths = []
        for line in lines:
            names = re.findall("a_book_chapter_\d+_\d+\.dat", line)
            if names:
                paths.append("book/chapter/" + names[0])
        return sorted(paths, cmp_path)

    def ftp_list(self, path):
        lines = []
        def cb(line):
            lines.append(line)

        retries = 0
        while True:
            try:
                if not self.ftp:
                    self.ftp_login()
                self.logger.debug("FTP LIST %s" % path)
                self.ftp.retrlines('LIST %s' % path, cb)
                break
            except:
                lines = []
                self.ftp = None
                retries += 1
                if retries >= 3:
                    raise
                time.sleep(30)

        return lines

    def ftp_parse_dat(self, path, row_processor):
        buf = [""]
        def cb(block):
            buf[0] += block  #refer to outer variable "buf", workaround for python2.x

            while True:
                index = buf[0].find("\r\n")
                if index != -1:
                    rowdata = buf[0][:index]
                    row = []
                    for item in rowdata.split("\x80"):
                        row.append(unicode(item, 'gbk', errors = 'ignore'))

                    try:
                        row_processor(row)
                    except:
                        self.logger.warning(get_exception_info())

                    buf[0] = buf[0][index+2:]
                else:
                    break

        retries = 0
        while True:
            try:
                if not self.ftp:
                    self.ftp_login()
                self.logger.debug("FTP RETR %s" % path)
                self.ftp.retrbinary('RETR %s' % path, cb)
                break
            except:
                self.ftp = None
                retries += 1
                if retries >= 3:
                    raise
                time.sleep(30)


class NovelCrawler(Crawler):
    type = "novel.cm.novel"

    def crawl(self):
        novel_id = self.key
        cm_novel = NovelCMNovelModel().find_one({"novel_id" : novel_id})
        if not cm_novel:
            raise Exception("novel_id - %s not found" % novel_id)

        source_id = cm_novel["novel_id"]

        cm_chapters = NovelCMChapterModel().find({"novel_id" : novel_id})
        if not cm_chapters:
            raise Exception("no chapter found for novel - %s" % novel_id)

        chapter_count = max(cm_chapters, key = lambda item : item['index'])['index'] + 1
        max_time = max(cm_chapters, key = lambda item : item['time'])['time']
        chapters = []
        for i in range(chapter_count):
            chapters.append({
                             "title" : "",
                             "price" : 0.0,
                             "url" : "",
                             })

        total_words = 0
        for cm_chapter in cm_chapters:
            total_words += cm_chapter["words"]
            price = cm_chapter["price"] * 0.01
            chapters[cm_chapter["index"]] = {
                                             "title" : cm_chapter["title"],
                                             "url" : "http://wap.cmread.com/r/l/r.jsp?vt=3&bid=%s&cid=%s&dolphin=1" % (cm_novel["novel_id"], cm_chapter["chapter_id"]),
                                             "price" : price,
                                             }
            if price == 0.0:
                data = {
                        "chapter_id" : cm_chapter["chapter_id"],
                        }
                Scheduler.schedule(ChapterCrawler.type,
                            key = "%s#%s" % (source_id, cm_chapter["index"]),
                            data = data,
                            priority = Priority.Low)


        url = "http://wap.cmread.com/r/l/v.jsp?bid=%s&vt=3&dolphin=1" % cm_novel["novel_id"]
        image = None
        visits = None
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            hxs = HtmlXPathSelector(text = resp.text)
            image = hxs.select("//div[@class='fl bkpic']/a/img/@src").extract()[0]
            image = urlparse.urljoin("http://wap.cmread.com", image)

            for text in hxs.select("//ul[@class='bkinfo']/li/text()").extract():
                results = re.findall(u"点击：([\.\d]+)万", text)
                if results:
                    visits = int(float(results[0]) * 10000)
                    break
                results = re.findall(u"点击：(\d+)", text)
                if results:
                    visits = int(results[0])
                    break
        except Exception:
            self.logger.warning(get_exception_info())

        cm_novel['category'] = cm_novel['category'].replace(u'-听书', "")

        novel = NovelSourceModel({
                   "source" : self.data['source'],
                   "source_id" : source_id,
                   "title" : cm_novel["title"],
                   "author" : cm_novel["author"],
                   "url" : url,
                   "image" : image,
                   "visits" : visits,
                   "category" : cm_novel["category"],
                   "tags" : cm_novel["tags"],
                   "description" : cm_novel["description"],
                   "chapters" : chapters,
                   "time" : max_time,
                   "words" : total_words,
                   "price" : int(cm_novel["price"]) * 0.01,
                   "completed" : int(cm_novel["status"]) == 0,
                 })
        export(novel)


class ChapterCrawler(Crawler):
    type = "novel.cm.chapter"

    def crawl(self):
        source_id, index = self.key.split("#")
        url = "http://wap.cmread.com/r/l/r.jsp"
        params = {
                  "bid" : source_id,
                  "cid" : self.data["chapter_id"],
                  "vt" : 3,
                  }
        headers = {
                   "Cookie" : "pageSize=-1"
                   }
        resp = requests.get(url, params = params, headers = headers)
        resp.raise_for_status()
        hxs = HtmlXPathSelector(text = resp.text)
        lines = hxs.select("//p[@class='content']/text()").extract()
        content = "\n".join(lines)
        if content:
            save_txt(self.data['source'], source_id, index, content)


def cmp_path(path1, path2):
    def get_number(path):
        m = re.match(".+_(\d+)_\d+_(\d+)\.dat", path)
        if not m:
            m = re.match(".+_(\d+)_(\d+)\.dat", path)
        if not m:
            return path
        return int(m.group(1)) * 1000 + int(m.group(2))


    d1 = get_number(path1)
    d2 = get_number(path2)
    if d1 == d2:
        return 0
    elif d1 > d2:
        return 1
    else:
        return -1

if __name__ == "__main__":

    data = {
            "last_rank" : {},
            "last_ibook_meta" : "",
            "last_ibook_chapter" : "",
            "last_abook_meta" : "",
            "last_abook_chapter" : "",
            }
    DATCrawler(data = data).crawl()

    NovelCrawler(key = "356214374").crawl()
