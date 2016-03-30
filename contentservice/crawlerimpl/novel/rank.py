#coding=utf8
import requests
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.novel import NovelRankModel
from contentservice.utils import get_exception_info

CATERANK_SPEC = [
                  {
                      "title" : u"热门",
                      "type" : u"hot",
                      "sources" : [("yicha", u"易查小说点击榜"), ("soso", u"排行"), ("yicha", u"ReadNovel金牌榜")],
                  },
                  {
                      "title" : u"全本",
                      "type" : u"complete",
                      "sources" : [("soso", u"全本"), ("yicha", u"红袖小说完结榜"), ("yicha", u"起点全本推荐")],
                  },

                  {
                      "title" : u"奇幻玄幻",
                      "type" : u"category.qihuanxuanhuan",
                      "sources" : [("baidu", u"奇幻"), ("baidu", u"玄幻")],
                  },
                  {
                      "title" : u"武侠仙侠",
                      "type" : u"category.wuxiaxianxia",
                      "sources" : [("baidu", u"武侠"), ("baidu", u"仙侠")],
                  },
                  {
                      "title" : u"现代都市",
                      "type" : u"category.xiandaidushi",
                      "sources" : [("baidu", u"都市")],
                  },
                  {
                      "title" : u"言情小说",
                      "type" : u"category.yanqingxiaoshuo",
                      "sources" : [("soso", u"言情")],
                  },
                  {
                      "title" : u"青春校园",
                      "type" : u"category.qingchunxiaoyuan",
                      "sources" : [("baidu", u"青春")],
                  },
                  {
                      "title" : u"耽美同人",
                      "type" : u"category.danmeitongren",
                      "sources" : [("soso", u"耽美"), ("baidu", u"同人")],
                  },
                  {
                      "title" : u"穿越架空",
                      "type" : u"category.chuanyuejiakong",
                      "sources" : [("baidu", u"穿越")],
                  },
                  {
                      "title" : u"官场职场",
                      "type" : u"category.guanchangzhichang",
                      "sources" : [("soso", u"官场")],
                  },
                  {
                      "title" : u"悬疑灵异",
                      "type" : u"category.xuanyilingyi",
                      "sources" : [("baidu", u"悬疑")],
                  },
                  {
                      "title" : u"文学经典",
                      "type" : u"category.wenxuejingdian",
                      "sources" : [("soso", u"经典")],
                  },
                  {
                      "title" : u"军事历史",
                      "type" : u"category.junshilishi",
                      "sources" : [("baidu", u"历史"), ("baidu", u"军事")],
                  },
                  {
                      "title" : u"游戏竞技",
                      "type" : u"category.youxijingji",
                      "sources" : [("baidu", u"网游")],
                  },
                  {
                      "title" : u"科幻小说",
                      "type" : u"category.kehuanxiaoshuo",
                      "sources" : [("baidu", u"科幻")],
                  },
                 ]

CATERANK_COUNT = 500

class CategoryCrawler(Crawler):
    type = "novel.rank.category"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(CategoryCrawler.type, priority = Priority.High, interval = 3600 * 8)

    def crawl(self):
        for spec in CATERANK_SPEC:
            try:
                novels_set = set()
                novels = []
                novel_lists = []
                count = CATERANK_COUNT / len(spec['sources'])
                for src, title in spec['sources']:
                    if src == "baidu":
                        novel_lists.append(self.crawl_baidu(title, count))
                    elif src == "soso":
                        novel_lists.append(self.crawl_soso(title, count))
                    elif src == "yicha":
                        novel_lists.append(self.crawl_yicha(title, count))

                for lst in novel_lists:
                    lst.reverse()

                hasmore = True
                while hasmore and len(novels) < CATERANK_COUNT:
                    hasmore = False
                    for lst in novel_lists:
                        if not lst:
                            continue
                        novel = lst.pop()
                        if lst:
                            hasmore = True
                        if novel not in novels_set:
                            novels_set.add(novel)
                            novels.append(novel)

                rank = NovelRankModel({
                                "source" : self.data['source'],
                                "title" : spec["title"],
                                "type" : spec["type"],
                                "novels" : novels,
                                })

                export(rank)
            except:
                self.logger.warning(get_exception_info())

    def crawl_baidu(self, title, count):
        cateid = baidu_title2cateid(title)
        pn = 1
        titles = []
        while len(titles) < count:
            url = "http://m.baidu.com/book/data/cate?pn=%s&cateid=%s" % (pn ,cateid)
            data = requests.get(url).json()
            if data.get('errno') != 0:
                break
            titles.extend([item['title'] for item in data['result']['cate']])
            pn += 1
        return titles

    def crawl_soso(self, title, count):
        '''
        http://book.soso.com/#!/bookstore/fenlei/
        '''
        title2groupid = {
                 u"排行" : 3,
                 u"全本" : 6,

                 u"玄幻" : 227,
                 u"奇幻" : 219,
                 u"科幻" : 212,
                 u"仙侠" : 231,
                 u"网游" : 226,
                 u"官场" : 205,
                 u"悬疑" : 230,
                 u"惊悚" : 211,
                 u"军事" : 208,
                 u"穿越" : 201,
                 u"都市" : 202,
                 u"言情" : 232,
                 u"青春" : 218,
                 u"校园" : 229,
                 u"耽美" : 203,
                 u"文艺" : 253,
                 u"名著" : 206,
                 u"经典" : 252,
                 }
        gid = title2groupid[title]

        titles = []
        page = 1
        while len(titles) < count:
            url = "http://book.soso.com/ajax?m=list_book&groupid=%s&start=%s" % (gid, page)
            data = requests.get(url).json()
            if not data.get('rows'):
                break
            titles.extend([item['resourcename'] for item in data['rows']])
            page += 1
        return titles

    def crawl_yicha(self, title, count):
        titles = []
        page = 0
        pagesize = 20
        while len(titles) < count:
            url = "http://tbook.yicha.cn/tb/fyb.y"
            params = {
                      "cate" : title,
                      "pno" : page,
                      "psize" : pagesize
                      }
            data = requests.get(url, params = params).json()
            if not data.get('records'):
                break
            titles.extend([item["name"] for item in data["records"]])
            page += 1
        return titles

class BaiduTitle2CateID(object):
    def __init__(self):
        self.cache = {}

    def __call__(self, title):
        if not self.cache:
            url = "http://m.baidu.com/book/data/cates"
            data = requests.get(url).json()
            for cat in data['result']['cates']:
                self.cache[cat['catename']] = cat['cateid']
        return self.cache[title]
baidu_title2cateid = BaiduTitle2CateID()

if __name__ == "__main__":
    CategoryCrawler().crawl()
