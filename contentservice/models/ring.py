#coding=utf8
from datetime import datetime
import re
from base import ContentModel, ModelBase
from contentservice.utils.text import extract_key

SOURCE_AUTHORITY = {
                    "dolphin" : 10,
                    "cm" : 9,
                    "ct" : 8,
                    "cu" : 7,
                    "duomi" : 6,
                    "shoujiduoduo" : 6,
                    "v3gp" : 5,
                    }

class RingBackModel(ContentModel):
    
    TYPE = "ring.ringback"
    FIELDS = {
            "source_id" : u"",
            "key" : u"",
            "artist" : u"",
            "album" : u"",
            "duration" : 0,
            "hot" : False,
            "new" : False,
            "purchase" : u"",
            "expires" : datetime.utcfromtimestamp(0), 
            "lyrics" : u"",
            "language" : u"",
            }
    INDEXES = [
               {"key" : [("source", 1), ("key" , 1)]},
               {"key" : [("source", 1), ("source_id", 1)]},
               {
                "key" : [("title", "text"), ("artist", "text"), ("album", "text"), ("description", "text"), ("lyrics", "text")],
                "weights" : {"title" : 10, "artist" : 5, "album" : 5, "description" : 1, "lyrics" : 1},
                "default_language" : "chinese",
                "language_override" : "language_textsearch",
                "name" : "text_index"
                }
               ]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(RingBackModel, self).__init__(dct, authority = authority)
            
    def find_one(self, query, *args, **kwargs):
        query['expires'] = {"$gte" : datetime.utcnow()}
        return super(RingBackModel, self).find_one(query, *args, **kwargs)
        
    def find(self, query = {}, *args, **kwargs):
        query['expires'] = {"$gte" : datetime.utcnow()}
        query['price'] = 2
        return super(RingBackModel, self).find(query, *args, **kwargs)
    
    def text_search(self, *args, **kwargs):
        f = kwargs.get('filter', {})
        f['expires'] = {"$gte" : datetime.utcnow()}
        kwargs['filter'] = f
        return super(RingBackModel, self).text_search(*args, **kwargs)

    def find_dup(self):
        dup = self.collection().find_one({"source" : self["source"], "source_id" : self["source_id"]})
        return self.wrap(dup)
        
    def __setitem__(self, key, value):
        super(RingBackModel, self).__setitem__(key, value)
        if key == "artist" or key == "title":
            self["key"] = extract_key(self.get("title", "")) + "#" + extract_key(self.get("artist", ""))

    def export(self):
        dct = super(RingBackModel, self).export()
        dct.pop('lyrics')
        return dct
                            
class RingBackRankModel(ContentModel):
    
    TYPE = "ring.ringbackrank"
    FIELDS = {
                "carrier" : u"",
                "type" : u"",
                "ringbacks" : [], #["_id"]
            }
    INDEXES = [
               {"key" : [("carrier", 1), ("type", 1)], "unique" : True}
               ]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(RingBackRankModel, self).__init__(dct, authority = authority)
                
    def find_dup(self):
        dup = self.collection().find_one({"carrier" : self["carrier"], "type" : self["type"]})
        return self.wrap(dup)
    
    def on_import(self):
        ids = []
        for ringback in self['ringbacks']:
            if is_uuid(ringback):
                if RingBackModel().find_one({"source" : self["carrier"], "_id" : ringback}):
                    ids.append(ringback)
            else:
                item = RingBackModel().find_one({"source" : self["carrier"], "key" : ringback})
                if item:
                    ids.append(item["_id"])
        self['ringbacks'] = ids
        
        self._import()

                            
class RingToneModel(ContentModel):
    
    TYPE = "ring.ringtone"
    FIELDS = {
                "key" : u"",
                "artist" : u"",
                "album" : u"",
                "duration" : 0,
                "hot" : False,
                "new" : False,
                "purchase" : u"",
                "lyrics" : u"",  
                "language" : u"",               
                }
    INDEXES = [
                {"key" : [("key", 1)], "unique" : True},
                {
                "key" : [("title", "text"), ("artist", "text"), ("album", "text"), ("description", "text"), ("lyrics", "text")],
                "weights" :  {"title" : 10, "artist" : 5, "album" : 5, "description" : 1, "lyrics" : 1},
                "default_language" : "chinese",
                "language_override" : "language_textsearch",
                "name" : "text_index"                
                }
               ]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(RingToneModel, self).__init__(dct, authority = authority)
                
    def find_dup(self):
        dup = self.collection().find_one({"key" : self["key"]})
        return self.wrap(dup)
    
    def __setitem__(self, key, value):
        super(RingToneModel, self).__setitem__(key, value)
        if key == "artist" or key == "title":
            self["key"] = extract_key(self.get("title", "")) + "#" + extract_key(self.get("artist", ""))    

    def export(self):
        dct = super(RingToneModel, self).export()
        dct.pop('lyrics')
        return dct            

class RingToneRankModel(ContentModel):
    
    TYPE = "ring.ringtonerank"
    FIELDS = {
                "type" : u"",
                "ringtones" : [], #["_id"]
             }
    INDEXES = [
               {"key" : [("type", 1)], "unique" : True}
               ]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(RingToneRankModel, self).__init__(dct, authority = authority)
                
    def find_dup(self):
        dup = self.collection().find_one({"type" : self["type"]})
        return self.wrap(dup)
    
    def on_import(self):
        ids = []
        for ringtone in self['ringtones']:
            if is_uuid(ringtone):
                if RingToneModel().find_one({"_id" : ringtone}):
                    ids.append(ringtone)
            else:
                item = RingToneModel().find_one({"key" : ringtone})
                if item:
                    ids.append(item["_id"])
        self['ringtones'] = ids
        
        self._import()

                
class RingSceneModel(ContentModel):
    TYPE = "ring.scene"
    FIELDS =  {
                "carrier" : u"",
                "icon" : u"",
                "icon_inactive" : u"", 
                "hot" : False,
                "new" : False,
                "ringtone" : u"", #id
                "ringback" : u"", #id
            }
    INDEXES = [
               {"key" : [("carrier" , 1), ("title", 1)], "unique" : True},
               {
                "key" : [("title", "text"), ("ringtone", "text"), ("ringback", "text"), ("description", "text")],
                "weights" : {"title" : 10, "ringtone" : 3, "ringback" : 3, "description" : 1},
                "default_language" : "chinese",
                "language_override" : "language_textsearch",
                "name" : "text_index"                   
                }
               ]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(RingSceneModel, self).__init__(dct, authority = authority)
                
    def find_dup(self):
        dup = self.collection().find_one({"carrier" : self["carrier"], "title" : self["title"]})
        return self.wrap(dup)
    
    def on_import(self):
        if is_uuid(self["ringtone"]):
            if not RingToneModel().find_one({"_id" : self["ringtone"]}):
                self["ringtone"] = ""
        else:
            ringtone = RingToneModel().find_one({"key" : self["ringtone"]})
            self["ringtone"] = ringtone["_id"] if ringtone else ""            

        
        if is_uuid(self["ringback"]):
            if not RingBackModel().find_one({"source" : self["carrier"], "_id" : self["ringback"]}):
                self["ringback"] =  ""
        else:
            ringback = RingBackModel().find_one({"source" : self["carrier"], "key" : self["ringback"]})
            self["ringback"] = ringback["_id"] if ringback else ""
        
        self._import()     
                
    
class RingSceneRankModel(ContentModel):
    TYPE = "ring.scenerank"
    FIELDS = {
                "carrier" : u"",
                "type" : u"",
                "scenes" : [], #id
                }
    INDEXES = [
               {"key" : [("carrier", 1), ("type", 1)], "unique" : True}
               ]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(RingSceneRankModel, self).__init__(dct, authority = authority)
                    
    def find_dup(self):
        dup = self.collection().find_one({"carrier" : self["carrier"], "type" : self["type"]})
        return self.wrap(dup)    

    def on_import(self):
        ids = []
        for scene in self['scenes']:
            if is_uuid(scene):
                if RingSceneModel().find_one({"carrier" : self["carrier"], "_id" : scene}):
                    ids.append(scene)
            else:
                item = RingSceneModel().find_one({"carrier" : self["carrier"], "title" : scene})
                if item:
                    ids.append(item["_id"])
        self['scenes'] = ids
        
        self._import()


class RingUserModel(ModelBase):
    TYPE = "ring.user"
    FIELDS = {
              "imsi" : u"",
              "carrier" : u"",
              "scenes" : [],
              "ringbacks" : [],
              "ringtones" : [],
              "scenes_visit" : [],
              "ringbacks_visit" : [],
              "ringtones_visit" : [],
              }
    INDEXES = [{"key" : [("imsi" , 1)], "unique" : True}]


class RingFeedbackModel(ModelBase):
    TYPE = "ring.feedback"
    FIELDS = {
              "time" : datetime.utcfromtimestamp(0),
              "user" : u"",
              "content" : u"",
              }
    

def is_uuid(text):
    m = re.match("^[0-9a-f]{32}$", text)
    return True if m else False