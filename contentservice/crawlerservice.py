import time
import logging
import os, signal, sys
from threading import Timer
from contentservice.utils import get_exception_info
from contentservice.utils.daemon import Daemon
from crawler import _CRAWLER_CONF, CrawlerConf, Crawler, Scheduler

logger = logging.getLogger("contentcrawler")

_RUNNING_CRAWLER = None
def _worker_timeout_handler():
    logger.info('WORKER TIMEOUT pid: %s.' % os.getpid())
    os.kill(os.getpid(), signal.SIGTERM)

def _worker_term_handler(signum, frame):
    global _RUNNING_CRAWLER
    if _RUNNING_CRAWLER:
        Scheduler.cancel(_RUNNING_CRAWLER["type"], _RUNNING_CRAWLER["key"], True)
    logger.info('WORKER TERMINATING pid: %s.' % os.getpid())
    os._exit(0)

def _service_worker(category):
    global _RUNNING_CRAWLER

    signal.signal(signal.SIGTERM, _worker_term_handler)
    start_time = time.time()

    while time.time() <= start_time + CrawlerConf._CRAWLER_PROCESS_MAX_TIME:

        item = Scheduler.fetch(category)

        _RUNNING_CRAWLER = item

        timer = Timer(item.get('timeout', CrawlerConf._CRAWLER_TIMEOUT_DEFAULT), _worker_timeout_handler)
        timer.start()

        c = Crawler.create(item["type"], item["key"], item["data"])
        if c:
            try:
                c.crawl()
                success = True
                logger.info("CRAWL SUCCEED %s" % c)
            except Exception:
                msg = get_exception_info()
                success = False
                logger.error("CRAWL FAILED %s, %s" % (c, msg))
        else:
            logger.warn("CRAWL CREATE FAILED %s" % item)
            success = False

        timer.cancel()
        _RUNNING_CRAWLER = None
        Scheduler.finish(item['type'], item['key'], c.data if c else {}, success)


class CrawlerService(Daemon):

    def __init__(self, pidfile):
        self._pids = {}
        self._processes = None
        self._crawlers = None
        self._terminating = False
        self._terminated = False
        super(CrawlerService, self).__init__(name="crawlerservice", pidfile = pidfile)

    @property
    def processes(self):
        if not self._processes:
            self._processes =  dict(_CRAWLER_CONF.processes)
        return self._processes

    @property
    def crawlers(self):
        if not self._crawlers:
            self._crawlers = dict(_CRAWLER_CONF.enabled_crawlers)
        return self._crawlers

    def run(self):
        Scheduler.check_timeout()
        signal.signal(signal.SIGTERM, self._term_handler)
        self._init_crawlers()
        self._init_workers()
        while not self._terminated:
            self._check_crawlers()
            self._check_workers()
            time.sleep(10)

    def _term_handler(self, signum, frame):
        self._terminating = True
        for pid in self._pids.keys():
            try:
                os.kill(pid, signal.SIGTERM)
            except:
                pass
        self._pids = {}
        self._terminated = True
        logger.info('SERVICE TERMINATING pid: %s.' % os.getpid())

    def _init_crawlers(self):
        for type, cls in self.crawlers.iteritems():
            cls.init(conf=_CRAWLER_CONF.get_crawler_conf(type))
            logger.info(' CRAWLER INITIALIZED. type(%s)' % type)

    def _init_workers(self):
        for category, count in self.processes.iteritems():
            for i in range(count):
                worker_info = (_service_worker, [category], {})
                pid = self._create_worker(*worker_info)
                if pid:
                   self._pids[pid] = worker_info

    def _create_worker(self, worker, args, kwargs):
        pid = os.fork()
        if not pid:
            worker(*args, **kwargs)
            sys.exit()
        return pid

    def _autorestart_workers(self):
        old_pids =  dict(self._pids)
        for pid, worker_info in old_pids.iteritems():
            pid, status = os.waitpid(pid, os.WNOHANG)
            if pid > 0 and (not self._terminating):
                del self._pids[pid]
                new_pid = self._create_worker(*worker_info)
                if new_pid:
                    self._pids[new_pid] = worker_info
                    logger.info(' WORKER RESTART. %s --> %s' % (pid, new_pid))
        logger.info('AUTO RESTART CHECKED. pids: %s' % [ x for x in self._pids.keys()] )

    """
      In api side, to support add remote command to db .
      In service daemon side, to  load remote command in db and make changes dynamically.
    """
    def _check_crawlers(self):
        #TODO: implement check db changes and update crawler
        pass

    def _check_workers(self):
        #TODO: implement check db changes and update worker process
        self._autorestart_workers()
