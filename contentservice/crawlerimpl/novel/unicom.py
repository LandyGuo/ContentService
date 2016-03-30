#coding=utf8
from datetime import datetime
from hashlib import md5
import urlparse, requests
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.novel import NovelSourceModel
from contentservice.utils import get_exception_info
from common import save_txt

SERVER = "http://iread.wo.com.cn"
CLIENT_ID = "1010"
KEY = "95DF02C701503A845AA30248E04BF9E0"
VERSION = "1"

CHANNEL_ID = "18127001" #for dolphin only

class NovelListCrawler(Crawler):
    type = "novel.unicom.novellist"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(NovelListCrawler.type, priority = Priority.High, interval = 86400 * 7)

    def crawl(self):
        pagecount = 20
        pagenum = 1

        errors = 0
        while True:
            try:
                data = api_getcntlist(APISource.client, APICntType.all, pagenum, pagecount, APIStatisticsType.update)
                total = data['total']
                if not data['message']:
                    break
                for item in data['message']:
                    if item['cnttype'] in [APICntType.book, APICntType.newspaper, APICntType.magzine, APICntType.cartoon]:
                        Scheduler.schedule(NovelCrawler.type, key = item['cntindex']) #TODO: reset?
                if pagenum * pagecount > total:
                    break
                pagenum += 1
            except:
                self.logger.warning(get_exception_info())
                errors += 1
                if errors >= 10:
                    break

class NovelCrawler(Crawler):
    type = "novel.unicom.novel"

    def crawl(self):
        cntindex = self.key
        data = api_cntdetail(APISource.client, cntindex, 0)
        item = data['message']

        novel = NovelSourceModel({
             'source' : self.data['source'],
             'source_id' : cntindex,
             'title' : item['cntname'],
             'author' : item.get('authorname'),
             'image' : item['icon_file'][0]['fileurl'] if item.get('icon_file') else None,
             'category' : item.get('catalogname'),
             'completed' : item.get('finishflag') != 2,
             'favorites' : item.get('favcount'),
             'visits' : item.get('uacount'),
             'comments' : item.get('comcount'),
             'description' : item.get('longdesc'),
             'price' : 0.12 if item.get('price') else 0.0,
             'words' : item.get('wordcount'),
             'url' : "http://iread.wo.com.cn/pages/3g/detail20.jsp?cntindex=%s&channelid=%s" % (cntindex, CHANNEL_ID),
             #deleted : status
             })

        pagenum = 1
        pagecount = 20
        chapters = []
        while True:
            data = api_chalist(APISource.client, cntindex, pagenum, pagecount, 0, APICntType.book)
            total = data['total']
            if not data['message']:
                break

            for volume in data['message']:
                volumename = volume.get('volumename')
                for chapter in volume['charptercontent']:
                    index = len(chapters)
                    price = 0.0 if index < item['beginchapter'] - 1 else 0.01

                    chapters.append({
                                     "title" : chapter['chaptertitle'],
                                     "url" : chapter["charpterWapurl"] + "&channelid=" + CHANNEL_ID,
                                     "price" : price,
                                     })
                    chapterdata = {
                                   "volumeallindex" : chapter['volumeallindex'],
                                   "chapterallindex" : chapter['chapterallindex'],
                                   }
                    #http://iread.wo.com.cn/stacks/getChapterContent.action?cntindex=10015678&chapterallindex=10015678001&beginchapter=4&cntid=10015678&volumeallindex=569752&chapterseno=1&charpterflag=3&orderid=10015678

                    if not price: #free chapter only
                        Scheduler.schedule(ChapterCrawler.type, key = "%s#%s" % (cntindex, index), \
                                       data = chapterdata, priority = Priority.Low)

            if len(chapters) >= total:
                break
            pagenum += 1

        novel['chapters'] = chapters
        export(novel)

class ChapterCrawler(Crawler):
    type = "novel.unicom.chapter"
    def crawl(self):
        source_id, index = self.key.split("#")
        data = api_wordsdetail(APISource.client, source_id, self.data['volumeallindex'], self.data['chapterallindex'])
        save_txt(self.data['source'], source_id, index, data['message'])

class APISource:
    wap = 1
    www = 2
    client = 3
    iptv = 4
    mobile = 5

class APICntType:
    all = 0
    book = 1
    newspaper = 2
    magzine = 3
    cartoon = 4
    ring = 5
    video = 6

class APIStatisticsType:
    search = 1
    click = 2
    favorite = 3
    order = 4
    comment = 5
    like = 6
    hot = 7
    update = 11

def api_getcntlist(source, cnttype, pagenum, pagecount, statisticstype):
    return call_api("/rest/openread/cnt/getcntlist", [source, cnttype, pagenum, pagecount], {"statisticstype": statisticstype})

def api_recommand(source, limit = 3, onlyfree = 1):
    return call_api("/rest/openread/cat/supercatlog/cntlist", [source], {"limit" : limit, "onlyfree" : onlyfree})

def api_cntdetail(source, cntindex, discountindex, userid = None, pageid = None):
    return call_api("/rest/openread/cnt/cntdetail", [source, cntindex, discountindex], {"userid" : userid, "pageid" : pageid})

def api_chalist(source, cntindex, curpage, limit, sorttype, cnttype, userid = "null", productpkgindex = None):
    return call_api("/rest/openread/cnt/chalist", [source, cntindex, curpage, limit, sorttype], {"cnttype" : cnttype, "userid" : userid, "productpkgindex" : productpkgindex})

def api_wordsdetail(source, cntindex, volumeallindex, chapterallindex, chapterflag = 1, cnttypeflag = 1, userid = "", pagecount = 0, pagenum = 0, chaptertype = 0):
    path_params = [source]
    query_params = {
                    "cntindex" : cntindex,
                    "volumeallindex" : volumeallindex,
                    "chapterallindex" : chapterallindex,
                    "charpterflag" : chapterflag,
                    "cnttypeflag" : cnttypeflag,
                    "userid" : userid,
                    "pagecount" : pagecount,
                    "pagenum" : pagenum,
                    #"chaptertype" : chaptertype,
                    }
    return call_api("/rest/openread/cnt/wordsdetail", path_params, query_params)

def api_cataloglist(source, curpage, limit, cnttype, onlyfree = 0, onlycatlog = 0):
    path_params = [source, curpage, limit]
    query_params = {
                    'cnttype' : cnttype,
                    'onlyfree' : onlyfree,
                    'onlycatlog' : onlycatlog,
                    }
    return call_api("/rest/openread/cat/catalog/list", path_params, query_params)

def api_catacntlist(source, catalogindex, curpage, limit, finishflag, neworhot = 1, statisticstype = APIStatisticsType.update, onlyfree = 0):
    path_params = [source, catalogindex, curpage, limit]
    query_params = {
                    'finishflag' : finishflag,
                    'neworhot' : neworhot,
                    'statisticstype' : statisticstype,
                    'onlyfree' : onlyfree,
                    }
    return call_api("/rest/openread/cat/catalog/cntlist", path_params, query_params)

def call_api(path, path_params = [], query_params = {}, headers = {}):
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    passcode = md5(timestamp + CLIENT_ID + VERSION + KEY).hexdigest()

    uri = urlparse.urljoin(SERVER, path)
    if not uri.endswith("/"):
        uri += "/"
    uri += "/".join(str(param) for param in path_params + [timestamp, CLIENT_ID, VERSION, passcode])

#    query_params['channel_id'] = CHANNEL_ID
    resp = requests.get(uri, params = query_params, headers = headers)
    resp.raise_for_status()
    data = resp.json()
    if data['code'] != "0000":
        raise Exception("Return code error %s" % data['code'])
    return data



if __name__ == "__main__":
#    NovelListCrawler().crawl()
    NovelCrawler(key = 10015678).crawl()
#     data = api_getcntlist(APISource.client, 1, 1, 20, 1)
#     data = api_cataloglist(APISource.client, 1, 100, APICntType.all)
#     for item in data['message']:
#         print item['catalogname']
#
#     data = api_cntdetail(APISource.client, 10005327, 0)
#    data = api_chalist(APISource.client, 10005327, 0, 20, 0, 0)
#    data = api_wordsdetail(APISource.client, 10015678, 569752, 10015678014)
#    print data
