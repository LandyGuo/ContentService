#coding=utf8
from contentservice.crawler import Crawler, Priority, export, Scheduler
from contentservice.models.video import VideoRankModel
from contentservice.utils import get_exception_info

TOP_SPEC = [
                  {
                      "title" : u"电影",
                      "type" : u"movie",
                      "sources" : [("youku", "http://movie.youku.com/top/"),
                                   ("iqiyi", 1),
                                   ("tudou", "movie"),
                                   ("sohu", "movie"),
                                   ("letv", u"电影"),
                                   ],
                  },
                  {
                      "title" : u"电视剧",
                      "type" : u"tv",
                      "sources" : [("iqiyi", 2),
                                   ("sohu", "tv"),
                                   ("youku", "http://tv.youku.com/top/"),
                                   ("tudou", "tv"),
                                   ("letv", u"电视剧"),
                                   ],
                  },
                  {
                      "title" : u"综艺",
                      "type" : u"zy",
                      "sources" : [
                                   ("sohu", "zy"),
                                   ("iqiyi", 6),
                                   ("youku", "http://zy.youku.com/top/"),
                                   ("letv", u"综艺"),
                                   ("tudou", "zy")
                                   ],
                  },
                 ]

TOP_COUNT = 500

class ChannelCrawler(Crawler):
    type = "video.rank.channel"

    @staticmethod
    def init(conf=None):
        if not conf:
            conf = {}
        Scheduler.schedule(ChannelCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 86400))

    def crawl(self):
        for spec in TOP_SPEC:
            video_set = set()
            videos = []
            count = TOP_COUNT / len(spec['sources'])

            for src, param in spec['sources']:
                func = getattr(self, "crawl_%s" % src)
                if func:
                    try:
                        titles = func(param, count)
                        for title in titles:
                            if title not in video_set:
                                video_set.add(title)
                                videos.append(title)
                    except:
                        self.logger.warning(get_exception_info())


            rank = VideoRankModel({
                            "source" : self.data['source'],
                            "title" : spec["title"],
                            "type" : spec["type"],
                            "videos" : videos,
                            })

            export(rank)


    def crawl_youku(self, url, count):
        import youku
        return youku.crawl_top(url)

    def crawl_sohu(self, type, count):
        import sohu
        return sohu.crawl_top(type)

    def crawl_iqiyi(self, cid, count):
        import iqiyi
        return iqiyi.crawl_top(cid)

    def crawl_letv(self, title, count):
        import letv
        return letv.crawl_top(title)

    def crawl_tudou(self, type, count):
        import tudou
        return tudou.crawl_top(type)


if __name__ == "__main__":
    ChannelCrawler().crawl()
