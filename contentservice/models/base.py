#coding=utf8
import logging, copy
from uuid import uuid4
from django.conf import settings
from pymongo import MongoClient
from contentservice.utils.typeutil import convert
from contentservice.utils.datetimeutil import unix_time
from contentservice.utils.text import clean_list, clean_text, clean_url, clean_paragraph
from datetime import datetime

_MONGO_CONN_STR = settings.MONGO_CONN_STR
_MONGO_CONN = None
_COLLECTIONS = {}

_LOGGER = logging.getLogger("contentimport")
_INSERT_LOGGER = logging.getLogger("inserted_video")
_UPDATE_LOGGER = logging.getLogger("updated_video")
_SKIP_LOGGER = logging.getLogger("skipped_video")

def get_conn():
    global _MONGO_CONN
    if not _MONGO_CONN:
        _MONGO_CONN = MongoClient(_MONGO_CONN_STR)
    return _MONGO_CONN

class ModelMeta(type):

    def __init__(self, name, bases, dct):
        fields = dct.get('FIELDS', {})
        base = bases[0]
        while base != object:
            for k, v in base.__dict__.get('FIELDS', {}).iteritems():
                fields[k] = v
            base = base.__base__
        dct['FIELDS'] = fields

        indexes = dct.get('INDEXES', [])
        base = bases[0]
        while base != object:
            indexes.extend(base.__dict__.get('INDEXES', []))
            base = base.__base__
        dct['INDEXES'] = indexes

        type.__init__(self, name, bases, dct)


class ModelBase(dict):

    __metaclass__ = ModelMeta

    TYPE = "base"
    FIELDS = {}
    INDEXES = []

    def __init__(self, dct = {}):
        if not isinstance(dct, dict):
            raise TypeError

        for key in self.FIELDS.iterkeys():
            self[key] = dct.get(key)

    def __setitem__(self, key, value):
        if key not in self.FIELDS:
            return #ignore

        t = type(self.FIELDS[key])

        if value is None:
            value = copy.deepcopy(self.FIELDS[key])
        elif not isinstance(value, t):
            value = convert(value, t)
            if value is None:
                raise TypeError

        super(ModelBase, self).__setitem__(key, value)

    def collection(self):
        if not _COLLECTIONS.get(self.TYPE):
            basename = "content"
            db_name = self.TYPE.split(".")[0]
            collection_name = self.TYPE
            _COLLECTIONS[self.TYPE] = get_conn()[basename + "_" + db_name][collection_name]

            for spec in self.INDEXES:
                key = spec["key"]
                kwargs = spec.copy()
                kwargs.pop("key")
                _COLLECTIONS[self.TYPE].ensure_index(key, **kwargs)

        return _COLLECTIONS[self.TYPE]

    def wrap(self, dct):
        if isinstance(dct, ModelBase):
            return dct
        elif isinstance(dct, dict):
            return type(self)(dct)
        else:
            return None

    def find_one(self, query = {}, fields = None):
        dct = self.collection().find_one(query, fields)
        return self.wrap(dct)

    def find(self, query = None, fields = None, skip = 0, limit = 0, sort = None):
        items = []
        for dct in self.collection().find(spec = query, fields = fields, skip = skip, limit = limit, sort = sort):
            items.append(self.wrap(dct))
        return items

    def text_search(self, query, min_score = 0, **kwargs):
        if not query:
            return []

        db = self.collection().database
        data = db.command("text", self.TYPE, search = query, **kwargs)
        results = data.get('results')
        items = []
        if results:
            for result in results:
                if result['score'] >= min_score:
                    items.append(self.wrap(result['obj']))
        return items


class ContentModel(ModelBase):

    TYPE = "base.content"
    FIELDS = {
                "_id": u"",
                "created": datetime.utcfromtimestamp(0),
                "updated": datetime.utcfromtimestamp(0),
                "authorities": {}, #{field : authority}
                "title": u"",
                "time": datetime.utcfromtimestamp(0),
                "image": u"",
                "image2": u"",
                "url": u"",
                "description": u"",
                "price": 0.0,
                "tags": [],
                "visits": 0,
                "comments": 0,
                "favorites": 0,
                "score": 0.0,
                "source": u"",
                "deleted": False,
             }
    INDEXES = [
                 {
                   "key" : [("updated", -1), ("_id", -1)],
                 },
              ]

    def __init__(self, dct = {}, authority = None):
        if not isinstance(dct, dict):
            raise TypeError

        if authority is None:
            authority = 0
        self.authority = authority

        authorities = dct.get('authorities', {})

        self["authorities"] = {}
        for key in self.FIELDS.iterkeys():
            if key != "authorities":
                self.set_field(key, dct.get(key), authorities.get(key))

    def __setitem__(self, key, value):
        return self.set_field(key, value)

    def set_field(self, field, value, authority = None):
        ret = super(ContentModel, self).__setitem__(field, value)
        if field in ["_id", "created", "updated", "authorities"]:
            return ret

        if (value is None) or self.is_empty(field):
            authority = -1

        if authority is None:
            authority = self.get_authority(field)
            if authority == -1:
                authority = self.authority

        self['authorities'][field] = authority
        return ret

    def get_authority(self, field):
        return self['authorities'].get(field, -1)

    def is_empty(self, field):
        defvalue = self.FIELDS[field]
        if isinstance(defvalue, bool):
            return False
        if field in ["price"]:
            return False

        return self[field] == defvalue

    def clean(self):
        for field in self.FIELDS.iterkeys():
            if field in ["_id", "created", "updated", "authorities"]:
                continue
            self[field] = self.clean_value(field, self[field])

    def clean_value(self, field, value):
        if field == "title":
            value = clean_text(value)
        elif field == "description":
            value = clean_paragraph(value)
        elif field in ["image", "image2", "url"]:
            value = clean_url(value)
        elif field == "tags":
            value = clean_list(value)
        return value

    def _import(self):
        self.clean()
        source = self['source']
        channel = self['channel']
        
        dup = self.find_dup()
        if dup:
            self["_id"] = dup["_id"]
            self["created"] = dup["created"]
 
            self.merge(dup)
            if not self.equals(dup):
                self.save()
                _LOGGER.info("UPDATED CONTENT - %s" % dup)
                if self.TYPE == "video.chapter":
                    _UPDATE_LOGGER.info(
                                        "UPDATED CONTENT {'source': '%s', 'channel': '%s', 'album_id': '%s', 'time': '%s', 'log_type': 'update'}",
                                        source,
                                        channel, 
                                        dup.get("album_id"),
                                        datetime.now()
                                        )
                     
            else:
                _LOGGER.info("SKIPPED CONTENT - %s" % dup)
                if self.TYPE == "video.chapter":
                    _SKIP_LOGGER.info(
                                      "SKIPPED CONTENT {'source': '%s', 'channel': '%s', 'album_id': '%s', 'time': '%s', 'log_type': 'skip'}",
                                      source,
                                      channel,
                                      dup.get("album_id"),
                                      datetime.now()
                                      )
        else:
            self.save()
            _LOGGER.info("INSERTED CONTENT - %s" % self)
            if self.TYPE == "video.chapter":
                _INSERT_LOGGER.info(
                                    "INSERTED CONTENT {'source': '%s', 'channel': '%s', 'album_id': '%s', 'time': '%s', 'log_type': 'insert'}", 
                                    source,
                                    channel,
                                    self.get("album_id"),
                                    datetime.now()
                                    )

    def save(self):
        _id = self.get("_id")
        if not _id or _id == -1:
            self["_id"] = self.new_id()
            self["created"] = datetime.utcnow()

        self["updated"] = datetime.utcnow()
        cond = {"_id" : self["_id"]}
        self.collection().update(cond, self, upsert = True)
        return self

    def new_id(self):
        return uuid4().hex

    def on_import(self):
        self._import()

    def export(self):
        dct = dict(self)
        dct["id"] = dct.pop("_id")
        dct.pop('authorities')
        dct.pop('created')
        return dct

    def find_dup(self):
        raise NotImplemented

    def merge(self, item):
        '''
        item: existing item in database
        '''
        for field in self.FIELDS.iterkeys():
            if field in ["_id", "created", "updated", "authorities"]:
                continue

            auth1 = self.get_authority(field)
            auth2 = item.get_authority(field)
            overwrite = auth1 < auth2

            value = self.merge_value(field, item[field], overwrite)
            self.set_field(field, value, auth2 if overwrite else auth1)

    def merge_value(self, field, value, overwrite):
        '''
        value: existing value, ***DO NOT MODIFY***
        overwrite: whether should value overwrite self[field]
        '''
        return value if overwrite else self[field]


    def equals(self, item):
        if self.__class__ != item.__class__:
            return False
        for k in self.FIELDS.keys():
            if k not in ["_id", "created", "updated"]: #TODO: authorities
                if isinstance(self[k], datetime):
                    if unix_time(self[k]) != unix_time(item[k]): #drop precise
                        return False
                elif self[k] != item[k]:
                    return False
        return True

    def __unicode__(self):
        return u"%s(%s, %s)" % (self.TYPE, self['_id'], self['title'])

    def __str__(self):
        return "%s(%s, %s)" % (self.TYPE, self['_id'], self['title'])
