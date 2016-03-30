#coding=utf8
from contentservice.crawler import Crawler, Priority, Scheduler


SOURCE_LIST = ['360','56','bdzy','douban','iqiyi','letv','sina','sohu','tencent','youku','tudou']


class RankCrawler(Crawler):
    type = "video.rank.top"
    
    @staticmethod
    def init(conf = None):
        if not conf:
            conf = {}
        Scheduler.schedule(RankCrawler.type, priority = conf.get('priority', Priority.High), interval = conf.get('interval', 86400))
    
    def crawl(self):
        for source in SOURCE_LIST:
            func = getattr(self,'crawl_%s' % source)
            func()
    
    def crawl_360(self):
        import top_360
        return top_360.TopCrawler().crawl()
    
    def crawl_56(self):
        import top_56
        return top_56.TopCrawler().crawl()
    
    def crawl_bdzy(self):
        import top_bdzy
        return top_bdzy.TopCrawler().crawl()
    
    def crawl_douban(self):
        import top_douban
        return top_douban.TopCrawler().crawl()
    
    def crawl_iqiyi(self):
        import top_iqiyi
        return top_iqiyi.TopCrawler().crawl()
    
    def crawl_letv(self):
        import top_letv
        return top_letv.TopCrawler().crawl()

    def crawl_sina(self):
        import top_sina
        return top_sina.TopCrawler().crawl()
    
    def crawl_sohu(self):
        import top_sohu
        return top_sohu.TopCrawler().crawl()
    
    def crawl_tencent(self):
        import top_tencent
        return top_tencent.TopCrawler().crawl()
    
    def crawl_youku(self):
        import top_youku
        return top_youku.TopCrawler().crawl()
    
    def crawl_tudou(self):
        import top_tudou
        return top_tudou.TopCrawler().crawl()
        
if __name__=="__main__":
    RankCrawler().crawl()