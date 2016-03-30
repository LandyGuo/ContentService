#coding=utf8
'''
http://www.shoujiduoduo.com/main/#
'''
import requests, urllib, json, re, random
from contentservice.crawler import Crawler, Scheduler, export
from contentservice.models.ring import RingToneModel, RingToneRankModel

SERVER = "http://www.shoujiduoduo.com"

SOURCE = "shoujiduoduo"

RANK2TYPE = {
#             u"最热" : "hot",
#             u"最新" : "new",
#             u"搞笑" : "joke",
#             u"流行金曲" : "pop",
             }

class RankListCrawler(Crawler):
    type = "ring.shoujiduoduo.ranklist"

    @staticmethod
    def init(conf=None):
        Scheduler.schedule(type = RankListCrawler.type, interval = 86400)

    def crawl(self):
        text = requests.get(SERVER + "/main/js/ring.js").text
        nav_list = re.findall("var\s+navList\s+=\s+'([^']+)';", text)[0]
        nav_list = json.loads(nav_list)
        for nav in nav_list:
            data = {
                    "id" : nav["id"],
                    "title" : nav["disname"],
                    }
            Scheduler.schedule(type = RankCrawler.type, key = nav["id"], data = data)


class RankCrawler(Crawler):
    type = "ring.shoujiduoduo.rank"

    def crawl(self):
        dcts = get_rings(self.data["id"])

        for dct in dcts:
            Scheduler.schedule(RingCrawler.type, key = dct['source_id'], data = dct, interval = 86400)

        rank_type = RANK2TYPE.get(self.data["title"])
        if rank_type:
            rings = [RingToneModel(dct)["key"] for dct in dcts]
            export(RingToneRankModel({
                               "source" : SOURCE,
                               "title" : self.data["title"],
                               "type" : rank_type,
                               "ringtones" : rings,
                               }))

class RingCrawler(Crawler):
    type = 'ring.shoujiduoduo.ring'

    def crawl(self):
        dct = self.data
        dct["source"] = SOURCE
        ring = RingToneModel(dct)
        export(ring)

def get_rings(list_id):
    page = 1

    ringtones = []
    while True:
        params = {
                  "type" : "getlist",
                  "listid" : list_id,
                  "page" : page,
                  }
        url = SERVER + "/ringweb/ringweb.php?" + urllib.urlencode(params)

        text = requests.get(url).text

        data = re.sub(",]", "]", text)
        items = json.loads(data)
        for item in items[1:]:
            url = "javascript: getUrl('shoujiduoduo', '%s');" % item["id"];
            visits = int(re.findall("\d+", item["playcnt"])[0]) * 100 + random.randint(0, 100)
            ringtone = {
                          "source_id" : item["id"],
                          "title" : item["name"].split("-")[0].strip(),
                          "artist" : item["artist"],
                          "visits" : visits,
                          "duration" : item["duration"],
                          "url" : url,
                        }
            ringtones.append(ringtone)
        if not items[0]["hasmore"]:
            break
        page += 1
    return ringtones


if __name__ == "__main__":
    RankCrawler(key = "7", data = {"id" : "7", "title" : "搞笑"}).crawl()

