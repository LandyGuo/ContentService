#coding=utf8
'''
http://player.pc.duomi.com/song-ajaxsong-playlist?id=45&type=rfl&pz=100&pi=1
'''
import requests
from contentservice.crawler import Crawler, export, Priority, Scheduler
from contentservice.models.ring import RingToneModel, RingToneRankModel
from contentservice.utils import get_exception_info

SERVER = "http://player.pc.duomi.com"
SOURCE = "duomi"

RANK_MAP = {
            u"多米下载榜" : {
                        "type" : u"hot",
                        "title" : u"热销"
                        }
            }

class RankCrawler(Crawler):
    type = "ring.duomi.rank"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(type = RankCrawler.type, priority = Priority.High, interval = 86400)

    def crawl(self):
        data = requests.get(SERVER + "/song-ajaxsong-classes").json()
        for category in data['data']:
            if category['name'] == u'铃声':
                for item in category['tree']:
                    try:
                        self.crawl_list(item['resourceid'], item['nodetypesub'], item['name'])
                    except Exception, e:
                        self.logger.warning(e)

        data = requests.get(SERVER + "/song-ajaxsong-ranks").json()

        for item in data['data']['tree']:
            try:
                self.crawl_list(item['resourceid'], item['nodetypesub'], item['name'])
            except Exception:
                self.logger.warning(get_exception_info())

    def crawl_list(self, list_id, list_type, list_title):
        if not RANK_MAP.get(list_title):
            return

        params = {
                  "id" : list_id,
                  "type" : list_type,
                  "pz" : 500,
                  "pi" : 1
                  }

        data = requests.get(SERVER + "/song-ajaxsong-playlist", params = params).json()

        keys = []
        for song in data['data']['songs']:
            ringtone = RingToneModel({
                                      "source_id" : song['id'],
                                      "title" : song['title'],
                                     # "url" : song.get('mediaurl'),
                                      "duration" : song.get('playlength'),
                                      "artist" : song['artists'][0]['name'] if song.get('artists') else None
                                      })
            keys.append(ringtone['key'])

        rank_import = RANK_MAP.get(list_title)
        if rank_import:
            export(RingToneRankModel({
                           'source' : SOURCE,
                           'type' : rank_import['type'],
                           'title' : rank_import['title'],
                           'ringtones' : keys,
                           }))

if __name__ == "__main__":
    RankCrawler().crawl()
