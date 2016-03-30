from datetime import datetime, timedelta
import socket
import time, logging
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from models.base import ContentModel
from contentservice.settings import MONGO_CONN_STR, CRAWLER_TIMEOUT_DEFAULT,\
                    CRAWLER_PROCESS_MAX_TIME

socket.setdefaulttimeout(10)

logger = logging.getLogger("contentcrawler")

class CrawlerStatus:
    NewAdded =  0
    Enabled = 1
    Disabled = 2


class CrawlerConf(object):

    _CRAWLER_PROCESS_MAX_TIME = CRAWLER_PROCESS_MAX_TIME
    _CRAWLER_TIMEOUT_DEFAULT = CRAWLER_TIMEOUT_DEFAULT
    _conn = MongoClient(MONGO_CONN_STR)
    _db = _conn["crawler"]

    def __init__(self):
        self._processes = None
        self._crawlers = None
        self._enabled_crawlers = None
        self._disabled_crawlers = None
        self._crawler_confs = {}

    def _query_processes(self):
        return dict([ (p['category'], int(p['count'])) for p in self._db['crawler_process'].find({})])

    @property
    def processes(self):
        if not self._processes:
            self._processes = self._query_processes()
        return self._processes

    @property
    def crawlers(self):
        if not self._crawlers:
            self._crawlers = self.query_crawlers()
        return self._crawlers

    @property
    def enabled_crawlers(self):
        if not self._enabled_crawlers:
            self._enabled_crawlers = self.query_crawlers(status=CrawlerStatus.Enabled)
        return self._enabled_crawlers

    @property
    def disabled_crawlers(self):
        if not self._disabled_crawlers:
            self._disabled_crawlers = self.query_crawlers(status=[CrawlerStatus.NewAdded, CrawlerStatus.Disabled])
        return self._disabled_crawlers

    def get_crawler_conf(self, crawler_type):
        if crawler_type not in self._crawler_confs:
            info = self._db['crawler_conf'].find_one({'type':crawler_type})
            if info:
                self._crawler_confs[crawler_type] = info
            return info
        else:
            return   self._crawler_confs[crawler_type]

    def query_crawlers(self, status=None):
        rets = {}
        cond = {}
        if status is not None:
            if isinstance(status, list):
                cond.update({'status':{'$in':status}})
            else:
                cond.update({'status':status})
        crawler_types = self.find_crawlers()
        #logger.info('FIND CRAWLER \n%s' % '\n'.join(sorted([ '%s,%s' % (k,v) for k,v in crawler_types.iteritems()])))
        crawlers = self._db['crawler_conf'].find(cond)
        for c in crawlers:
            cls = crawler_types.get(c['type'])
            if cls:
                rets[c['type']] = cls
        return rets

    def _find_crawlers(self, obj, depth = 0):
        crawler_types = {}
        if depth > 3:
            return
        if isinstance(obj, type) and issubclass(obj, Crawler) and obj != Crawler:
            crawler_types[obj.type] = obj
        elif type(obj).__name__ == "module":
            for key in dir(obj):
                if not key.startswith("__"):
                    ctypes = self._find_crawlers(getattr(obj, key), depth + 1)
                    if ctypes:
                        crawler_types.update(ctypes)
        return crawler_types

    def find_crawlers(self):
        import crawlerimpl
        return self._find_crawlers(crawlerimpl)

_CRAWLER_CONF = CrawlerConf()


class Crawler(object):
    type = "base.crawler"

    def __init__(self, **kwargs):
        self.key = kwargs.get('key', "")
        self.data = kwargs.get('data', {})
        self.logger = logging.getLogger("contentcrawler")

    @staticmethod
    def init(conf={}):
        pass

    @staticmethod
    def create(type, key, data):
        cls = _CRAWLER_CONF.enabled_crawlers.get(type)
        category, source, name = tuple(type.split('.'))
        if not data:
            data = {}
        data.update({'source': source})
        if not cls:
            return None
        return cls(key = key, data = data)

    def crawl(self):
        raise NotImplemented

    def __str__(self):
        return "Crawler(%s, %s, %s)" % (self.type, self.key, self.data)

class Priority:
    High2 = 2
    High = 1
    Normal = 0
    Low = -1

class Status:
    NotStart =  0
    Running = 1
    Succeed = 2
    Failed = -1
    Canceling = -2

class Scheduler(object):

    _conn = MongoClient(MONGO_CONN_STR)
    _db = _conn["crawler"]
    _collections = {}

    @staticmethod
    def collection(crawler_type):
        type_category = crawler_type.split(".")[0]

        if not Scheduler._collections.get(type_category):
            collection = Scheduler._db[type_category]
            collection.ensure_index([("type", 1), ("key", 1)], unique = True)
            collection.ensure_index([("status", 1)])
            collection.ensure_index([("priority", 1), ("nextrun", 1)])
            collection.ensure_index([("data.url", 1),])
            Scheduler._collections[type_category] = collection
        return Scheduler._collections[type_category]
    
    @staticmethod
    def monitor_schedule(type, nextrun=None):
        existing = Scheduler.collection(type).find({"type": type})
        
        if existing:
            for item in existing:
                Scheduler.schedule(
                                   type=type, 
                                   key=item['key'], 
                                   data=item['data'], 
                                   priority=item["priority"] + 2, 
                                   interval=item['interval'],
                                   reset=True
                                   )
            return True
        return False

    @staticmethod
    def schedule(type, key = "", data = None, priority = Priority.Normal, interval = 0, \
                 timeout = CrawlerConf._CRAWLER_TIMEOUT_DEFAULT, reset = False):
        if not isinstance(key, basestring):
            key = str(key)

        existing = Scheduler.collection(type).find_one({"type" : type, "key" : key})
        if existing:
            modifier = {}
            if existing['priority'] < priority: #priority can be upgraded
                modifier["priority"] = priority
            if existing.get('interval', 0) != interval: #update interval
                modifier["interval"] = interval
            if existing.get('timeout', CrawlerConf._CRAWLER_TIMEOUT_DEFAULT) != timeout: #update timeout
                modifier["timeout"] = timeout

            if reset:
                modifier["nextrun"] = datetime.utcnow()
                modifier["data"] = data
                if existing['status'] == Status.Running:
                    Scheduler.cancel(type, key)
                elif existing['status'] in [Status.Failed, Status.Succeed]:
                    modifier['status'] = Status.NotStart

            if modifier:
                modifier["priority"] = existing["priority"] + 1
                if modifier["priority"] > Priority.High2:
                    modifier["priority"] = Priority.High2
                    
                Scheduler.collection(type).update({"type" : type, "key" : key}, {"$set" : modifier})
        else:
            doc = {
               "type" : type,
               "key" : key,
               "data" : data,
               "priority" : priority,
               "interval" : interval,
               "timeout" : timeout,
               "lastrun" : datetime.min,
               "nextrun" : datetime.utcnow(),
               "status" : Status.NotStart
               }
            try:
                doc["priority"] += 1
                if doc["priority"] > Priority.High2:
                    doc["priority"] = Priority.High2
                    
                Scheduler.collection(type).insert(doc)
            except DuplicateKeyError:
                pass

    @staticmethod
    def schedule_url(url, data = None, priority = Priority.High2, interval = 3600, \
                 timeout = CrawlerConf._CRAWLER_TIMEOUT_DEFAULT, reset = False):
        type, key = Scheduler._extract_url(url)
        if type and key:
            if not data:
                data = {'url':url}
            else:
                data.update({'url':url})
            Scheduler.schedule(type, key, data=data, priority=priority, interval=interval,
                              timeout=timeout, reset=reset)
            return True
        else:
            return False



    @staticmethod
    def _extract_url(url):
        for crawler_type, cls in _CRAWLER_CONF.enabled_crawlers.iteritems():
            if hasattr(cls, 'extract_key'):
                try:
                    key = cls.extract_key(url)
                    if key:
                        return crawler_type, key
                except:
                    pass
        return None, None


    @staticmethod
    def fetch(category):
        while True:
            item = Scheduler.fetch_nonblock(category)
            if item:
                return item
            time.sleep(10)

    @staticmethod
    def fetch_nonblock(category):
        cond = {"nextrun": {"$lte": datetime.utcnow()}, "status": Status.NotStart}
        modifier = {"$set": {"status": Status.Running, "lastrun": datetime.utcnow()}}
        sort = [("nextrun", 1), ("priority", -1)]

        doc = Scheduler.collection(category).find_and_modify(query = cond, sort = sort, update = modifier, new = True)
        if doc:
            return doc
        return None

    @staticmethod
    def finish(type, key, data = None, success = True):
        doc = Scheduler.collection(type).find_one({"type" : type, "key" : key})
        if not doc:
            return

        modifier = {}
        if doc["status"] == Status.Canceling:
            modifier = {"status" : Status.NotStart}
        elif doc["status"] == Status.Running:
            if doc.get("interval", 0) > 0:
                modifier["nextrun"] = datetime.utcnow() + timedelta(seconds = doc["interval"])
                modifier["status"] = Status.NotStart
            else:
                modifier["status"] = Status.Succeed if success else Status.Failed
                modifier["nextrun"] = datetime.max
            if data:
                modifier["data"] = data
        else:
            return
        
        modifier["priority"] = _CRAWLER_CONF.get_crawler_conf(type).get('priority')
        Scheduler.collection(type).update({"type" : type, "key" : key}, {"$set" : modifier})

    @staticmethod
    def cancel(crawler_type, key, force = False):
        if force:
            cond = {"type" : crawler_type, "key" : key, "status" : {"$in" : [Status.Running, Status.Canceling]}}
            modifier = {"$set" : {"status" : Status.NotStart}}
        else:
            cond = {"type" : crawler_type, "key" : key, "status" : Status.Running}
            modifier = {"$set" : {"status" : Status.Canceling}}
        Scheduler.collection(crawler_type).update(cond, modifier)

    @staticmethod
    def get_job_from_url(url):
        for type in _CRAWLER_CONF.processes.keys():
            job = Scheduler.collection(type).find_one({"data.url":url})
            if job:
                return job


    @staticmethod
    def get_job(type, key):
        Scheduler.collection(type).find_one({"type" : type, "key" : key})


    @staticmethod
    def get_data(type, key):
        item = Scheduler.get_job(type, key)
        return item.get('data') if item else None

    @staticmethod
    def check_timeout():
        for crawler_type in _CRAWLER_CONF.crawlers.iterkeys():
            cond = {
                    "status" : {"$in" : [Status.Running, Status.Canceling]},
                    }
            for item in Scheduler.collection(crawler_type).find(cond):
                if item["lastrun"] + timedelta(seconds = item.get("timeout", CrawlerConf._CRAWLER_TIMEOUT_DEFAULT)) < datetime.utcnow():
                    Scheduler.finish(item["type"], item["key"], success = False)

def export(data):
    assert isinstance(data, ContentModel)
    data.on_import()


if __name__ == "__main__":
    pass

"""
db.crawler_process.save({'category':'video','count':3, updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_process.save({'category':'novel','count':16, updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_process.save({'category':'ring','count':0,  updated:ISODate("2013-10-24T12:52:51.160Z")})
"""

"""
db.crawler_conf.save({'type':'novel.baidu.category','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.baidu.categorylist','status':1,'priority':0,'interval':86400,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.baidu.chapter','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.baidu.novel','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.baidu.top','status':1,'priority':0,'interval':86400,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.cm.chapter','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.cm.dat','status':1,'priority':0,'interval':86400,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.cm.novel','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.luoqiu.chapter','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.luoqiu.novel','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.luoqiu.novellist','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.rank.category','status':1,'priority':0,'interval':28800,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.shanwen.chapter','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.shanwen.novel','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.shanwen.novellist','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.unicom.chapter','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.unicom.novel','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.unicom.novellist','status':1,'priority':0,'interval':86400,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.yqxw.chapter','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.yqxw.novel','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'novel.yqxw.novellist','status':1,'priority':0,'interval':86400,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.bdzy.album','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.bdzy.list','status':1,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.fangying.history','status':1,'priority':0,'interval':86400,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.fangying.relation','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.hakuzy.album','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.hakuzy.list','status':1,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.iqiyi.album','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.iqiyi.category','status':1,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.iqiyi.top','status':1,'priority':1,'interval':0,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.iqiyi.v','status':1,'priority':1,'interval':600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.letv.top','status':0,'priority':1,'interval':86400,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.letv.list','status':0,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.letv.album','status':0,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.rank.channel','status':1,'priority':1,'interval':86400,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.sohu.album','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.sohu.category','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.youku.album','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.youku.category','status':1,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.youku.top','status':1,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.zy265.album','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.zy265.list','status':1,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.zyqvod.album','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.zyqvod.list','status':1,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.tudou.list','status':0,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.tudou.album','status':0,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.tencent.list','status':0,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.tencent.album','status':0,'priority':1,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
db.crawler_conf.save({'type':'video.rank.top','status':1,'priority':1,'interval':86400,updated:ISODate("2013-10-24T12:52:51.160Z")} 
"""
#db.crawler_conf.save({'type':'ring.duomi.rank','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.mobile.artist','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.mobile.artistid','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.mobile.music','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.mobile.rank','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.shoujiduoduo.rank','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.shoujiduoduo.ranklist','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.shoujiduoduo.ring','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.telecom.artist','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.telecom.artistid','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.telecom.artistlist','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.telecom.billboard','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.telecom.imusicrank','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.telecom.song','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.unicom.worank','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.v3gp.rank','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.v3gp.ranklist','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
#db.crawler_conf.save({'type':'ring.v3gp.ring','status':1,'priority':0,'interval':3600,updated:ISODate("2013-10-24T12:52:51.160Z")})
