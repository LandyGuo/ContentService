# coding=utf8
from datetime import datetime
from base import ContentModel, ModelBase
from datamap import tag_mapping, map_channel, map_classification
from contentservice.utils.text import clean_list, clean_text, clean_title, clean_url, clean_paragraph, is_uuid

CHANNEL_DICT = {
    u"动漫": u"animate",
    u"电影": u"film",
    u"热点": u"hot",
    u"搞笑": u"joke",
    u"电视剧": u"tv",
    u"综艺": u"variety",
    u"福利": u"welfare",
}

INNERMAP_SOURCE = ['iqiyi']

MAP_DICT = {}

LEVEL_ONE = u"channel"
LEVEL_TWO_LIST = [u"category", u"region"]

SOURCE_AUTHORITY = {
    "dolphin": 100,
    "youku": 95,
    "sohu": 90,
    "iqiyi": 85,
    "letv": 80,
    "tudou": 75,
    "douban": 60,
    "fangying": 50,
    "bdzy": 40,
    "hakuzy": 32,
    "zy265": 31,
    "zyqvod": 30,
}


class VideoSourceModel(ContentModel):
    TYPE = "video.source"
    FIELDS = {
        "source_id": u"",
        "actors": [],
        "directors": [],
        "categories": [],
        "duration": 0,
        "channel": u"",
        "region": u"",
        "completed": True,
        "pubtime": datetime.utcfromtimestamp(0),
        "related": [],  # [title, title], related videos
        "videos": [],
        "to_album_id": "",
    }
    INDEXES = [
        {"key": [("source", 1), ("source_id", 1)], "unique": True},
    ]

    def __init__(self, dct={}, authority=None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(VideoSourceModel, self).__init__(dct, authority=authority)

    def find_dup(self):
        if self.get('to_album_id'):
            dup = self.collection().find_one(
                {"source": self["source"], "to_album_id": self["to_album_id"]})
        if not self.get('to_album_id'):
            dup = self.collection().find_one(
                {"source": self["source"], "source_id": self["source_id"]})
        return self.wrap(dup)

    def clean_value(self, field, value):
        return value  # leave original value

    def on_import(self, to_album_id=''):
        if to_album_id:
            self['to_album_id'] = to_album_id
        if self['source'] and self['source_id']:
            self._import()

        album = self.to_album()
        album._import()

        chapter = self.to_chapter(
            album_id=album["_id"], channel=album['channel'])
        if chapter:
            chapter._import()

        if not to_album_id:
            self['to_album_id'] = album['_id']
            self.save()

    def to_album(self):
        album = VideoAlbumModel(self, authority=self.get_authority("source"))
        album['_id'] = self['to_album_id']
        album['channel'] = map_channel(self['channel'])
        if album['source'] in INNERMAP_SOURCE:
            item_dict = tag_mapping(
                album['source'], album['channel'], album['tags'])
            album['categories'] = item_dict.get('categories')
            album['region'] = item_dict.get('region')
        else:
            album["categories"] = [map_classification(album['channel'], LEVEL_TWO_LIST[0], category)
                                   for category in self['categories']]
            album['region'] = map_classification(
                album['channel'], LEVEL_TWO_LIST[1], self['region'])

        if self['source'] and self['source_id']:
            album['sources'] = {
                self['source']: {
                    "id": self["source_id"],
                    "url": self["url"],
                    "price": self["price"],
                }
            }

        if self["related"]:
            related = []
            for item in VideoAlbumModel().find({"title": {"$in": self['related']}}, {"_id": True}):
                related.append(item["_id"])
            album['related'] = related
        return album

    def to_chapter(self, album_id, channel):
        if not self["videos"]:
            return
        return VideoChapterModel({
                                 "album_id": album_id,
                                 "videos": self["videos"],
                                 "source": self["source"],
                                 "channel": channel
                                 }, authority=self.get_authority('source'))


class VideoAlbumModel(ContentModel):
    TYPE = "video.album"
    FIELDS = {
        "actors": [],
        "directors": [],
        "categories": [],
        "duration": 0,
        "channel": u"",
        "region": u"",
        "completed": True,
        "pubtime": datetime.utcfromtimestamp(0),
        "related": [],  # [id, id], related videos
        "sources": {},  # {"youku": {url, price}}
    }

    INDEXES = [
        {"key": [("title", 1)]},
        {"key": [("source", 1), ("updated", 1)]},
    ]

    def __init__(self, dct={}, authority=None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(VideoAlbumModel, self).__init__(dct, authority=authority)

    def find_dup(self):
        _id = self.get('_id')
        if _id == -1:
            return None
        if _id:
            dup = self.collection().find_one({"_id": self["_id"]})
        else:
            dup = self.collection().find_one(
                {"channel": self["channel"], "title": self["title"]})
        return self.wrap(dup)

    def clean_value(self, field, value):
        if field in ["actors", "directors", "categories", "related"]:
            value = clean_list(value)
        elif field in ["channel", "region"]:
            value = clean_text(value)
        elif field in ["title"]:
            value = clean_title(value)
        else:
            value = super(VideoAlbumModel, self).clean_value(field, value)
        return value

    def merge_value(self, field, value, overwrite):
        if field == "sources":
            for k, v in value.iteritems():
                # if (not self[field].get(k)) or overwrite:
                self[field][k] = v  # always use new value
            return self[field]
        elif field == "tags":
            return list(set(self[field] + value))
        else:
            return super(VideoAlbumModel, self).merge_value(field, value, overwrite)

    def get_chapters(self):
        chapters = VideoChapterModel().find({'album_id': self['_id']})
        chapters = sorted(chapters, lambda x, y: 1 if x.get_authority(
            "videos") < y.get_authority("videos") else -1)
        return chapters

    def export(self):
        dct = super(VideoAlbumModel, self).export()
        chapters = self.get_chapters()

        videos = chapters[0]["videos"] if chapters else []
        dct['total_videos'] = len(videos)
        dct['last_video'] = videos[-1]['title'] if videos else ''
        return dct


class VideoChapterModel(ContentModel):
    TYPE = "video.chapter"
    FIELDS = {
        "album_id": u"",
        "channel": u"",
        "videos": [],  # videoitem
    }

    INDEXES = [{"key": [("album_id", 1), ("source", 1)], "unique": True},
               {"key": [("source", 1), ("updated", 1)]}]

    def clean_value(self, field, value):
        if field == "videos":
            videos = []
            for item in value:
                video = VideoItemModel(item)
                video.clean()
                videos.append(dict(video))
            value = videos
        else:
            value = super(VideoChapterModel, self).clean_value(field, value)
        return value

    def find_dup(self):
        dup = self.collection().find_one(
            {"album_id": self["album_id"], "source": self["source"]})
        return self.wrap(dup)


class VideoItemModel(ModelBase):
    TYPE = "video.item"
    FIELDS = {
        "title": u"",
        "url": u"",
        "image": u"",
        "price": 0.0,
        "duration": 0,
        "description": u"",
        "time": datetime.utcfromtimestamp(0),
        "stream": [],  # [{"url", "format", "size", "duration"}]
        "stream_high": [],
        "stream_low": [],
    }

    def clean(self):
        self["title"] = clean_text(self["title"])
        self["image"] = clean_url(self["image"])
        self["description"] = clean_paragraph(self["description"])
        return self


class VideoRankModel(ContentModel):
    TYPE = "video.rank"
    FIELDS = {
        "type": u"",
                "videos": [],  # ["title"]
    }
    INDEXES = [{"key": [("type", 1)], "unique": True}]

    def __init__(self, dct={}, authority=None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(VideoRankModel, self).__init__(dct, authority=authority)

    def find_dup(self):
        dup = self.collection().find_one({"type": self["type"]})
        return self.wrap(dup)

    def on_import(self):
        ids = []
        for video in self["videos"]:
            if is_uuid(video):
                ids.append(video)
            else:
                item = VideoAlbumModel().find_one(
                    {"title": video, "deleted": False})
                if item:
                    ids.append(item["_id"])

        self['videos'] = ids
        self._import()


class VideoTopModel(VideoRankModel):
    TYPE = 'video.top'
    FIELDS = {
        'type': '',  # 'mv.bdzy.top'
        'channel': '',  # '电影'
        'source': '',  # 360,bdzy
        'priority': 0,
        'updatetime': '',
        'list': []  # [{title:'',rank:0}]
    }

    def __init__(self, dct={}, authority=None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source', ''), 0)
        super(VideoTopModel, self).__init__(dct, authority=authority)

    def on_import(self):
        self._import()
