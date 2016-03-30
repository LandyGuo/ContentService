#coding=utf8
import copy, os
from datetime import datetime
from hashlib import md5
from base import ContentModel, ModelBase
from common import load_map
from contentservice.utils.novelutil import extract_chapter_number, extract_chapter_key
from contentservice.utils.text import clean_text, clean_url, is_uuid

SOURCE_AUTHORITY = {
                    "dolphin" : 100,
                    "baidu" : 95,
                    "duoku" : 80,
                    "cm" : 62,
                    "unicom" : 61,
                    "luoqiu" : 50,
                    "shanwen" : 45,
                    "yqzw" : 40,                    
                    }

class NovelSourceModel(ContentModel):
    TYPE = "novel.source"
    FIELDS = {
               "source_id" : u"",
               "author" : u"",
               "category" : u"",
               "words" : 0,
               "completed" : True,
               "chapters" : [], #{"title" : u"", "url" : u"", "price" : 0.0}       
              }
    INDEXES = [{"key" : [("source", 1), ("source_id", 1)], "unique" : True}]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(NovelSourceModel, self).__init__(dct, authority = authority)
                   
    def find_dup(self):
        dup = self.collection().find_one({"source" : self["source"], "source_id" : self["source_id"]})
        return self.wrap(dup)
    
    def clean_value(self, field, value):
        if field in ["author", "category"]:
            value = clean_text(value)
        elif field == "chapters":
            for chapter in value:
                chapter["title"] = clean_text(chapter.get("title"))
                chapter["url"] = clean_text(chapter.get("url"))                
            value = super(NovelSourceModel, self).clean_value(field, value)
        return value
    
    def txt_path(self, index):
        id_hash = md5(self["source_id"].encode('utf8')).hexdigest()
        path = u"%s/%s/%s/%s/%s.txt.gz" % (self["source"], id_hash[:2], id_hash[2:4], self["source_id"], index)
        return path
    
    def on_import(self): 
        if self["source"] and self["source_id"]:
            self._import()
        
        novel = self.to_novel()
        novel._import()
        
        chapter = self.to_chapter(novel_id = novel["_id"])
        if chapter:
            chapter._import()

    def to_novel(self):
        novel = NovelModel(self, authority = self.get_authority("source"))
        novel['_id'] = ''
        novel['category'] = map_category(self['category'], self['source'])
        novel['visits'] = normalize_visits(self['visits'], self['source'])
        if self["source"] and self["source_id"]:
            novel['sources'] = {
                                self['source'] : {
                                                  "id" : self["source_id"],
                                                  "url" : self["url"],
                                                  "price" : self["price"],                                              
                                                  }
                                }
        return novel
    
    def to_chapter(self, novel_id):
        if not self["chapters"]:
            return None
        
        chapters = []
        for i in range(len(self['chapters'])):
            item = self['chapters'][i]
            chapter = {
                         "title" : item["title"],
                         "sources" : {
                              self["source"] : {
                                                "id" : self["source_id"],
                                                "index" : i,
                                                "url" : item["url"],
                                                "price" : item["price"],  
                                                }
                              }
                        }
            chapters.append(chapter)
            
        return NovelChapterModel({
                           "novel_id" : novel_id,
                           "chapters" : chapters,
                           "source" : self["source"],                       
                           }, authority = self.get_authority('source'))
    

class NovelModel(ContentModel):
    TYPE = "novel.novel"
    FIELDS = {
               "author" : u"",
               "category" : u"",
               "words" : 0,
               "completed" : True,
               "sources" : {}, #{"baidu" : {"url":"","price":0}}
              }
    INDEXES = [{"key" : [("title", 1)]},
               {"key" : [("source", 1), ("updated", 1)]},]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(NovelModel, self).__init__(dct, authority = authority)
        
    def find_dup(self):        
        dup = self.collection().find_one({"title" : self["title"], "author" : self["author"]})
        return self.wrap(dup)

    def clean_value(self, field, value):
        if field in ["author", "category"]:
            value = clean_text(value)
        else:
            value = super(NovelModel, self).clean_value(field, value)
        return value
        
    def merge_value(self, field, value, overwrite):
        if field == "sources":
            for k, v in value.iteritems():
                #if overwrite or (not self[field].get(k)):
                self[field][k] = v #always use new value
            return self[field]
        elif field == "tags":
            return list(set(self[field] + value))
        else:        
            return super(NovelModel, self).merge_value(field, value, overwrite)
        
    def get_chapters(self):
        item = NovelChapterModel().find_one({"novel_id" : self["_id"]})
        return item['chapters'] if item else []
    
    def export(self):
        dct = super(NovelModel, self).export()
        chapters = self.get_chapters()
        dct['last_chapter'] = chapters[-1]["title"] if chapters else ""
        dct['total_chapters'] = len(chapters)
        return dct


class NovelChapterModel(ContentModel):
    TYPE = "novel.chapter"
    FIELDS = {
              "novel_id" : u"",
              "chapters" : [], #{"title" : "", "sources" : {"baidu" : {"url":"", "price":0, "id":xx, "index":0}}}
              }
    INDEXES = [{"key" : [("novel_id" , 1)], "unique" : True},
               {"key" : [("source", 1), ("updated", 1)]}]

    def find_dup(self):
        dup = self.collection().find_one({"novel_id" : self["novel_id"]})
        return self.wrap(dup)

    def clean_value(self, field, value):
        if field == "chapters":
            for chapter in value:
                chapter["title"] = clean_text(chapter.get("title"))
                for src in chapter["sources"].itervalues():
                    src["url"] = clean_url(src.get("url"))
        else:
            value = super(NovelChapterModel, self).clean_value(field, value)
        return value
    
    def merge_value(self, field, value, overwrite):
        if field == "chapters":
            if overwrite:
                return self.merge_chapters(copy.deepcopy(value), self[field], True) #do not modify value
            else:
                return self.merge_chapters(self[field], value, False)
        else:        
            return super(NovelChapterModel, self).merge_value(field, value, overwrite)
        
    def merge_chapters(self, des, src, overwrite = True):
        '''
        merge src to des (using des index)
        will modify des
        '''         
        def merge_chapter(des, src):
            for k, v in src["sources"].iteritems():
                if des["sources"].has_key(k) and (not overwrite):
                    continue
                des["sources"][k] = copy.deepcopy(v)
        
        key_cache = {}
        def extract_key_cached(title):
            if not key_cache.has_key(title):
                key_cache[title] = extract_chapter_key(title)
            return key_cache[title]
        
        number_cache = {}
        def extract_number_cached(title):
            if not number_cache.has_key(title):
                number_cache[title] = extract_chapter_number(title)
            return number_cache[title]
        
        def chapter_equal(title1, title2):
            key1 = extract_key_cached(title1)
            key2 = extract_key_cached(title2)
            s1, ch1 = extract_number_cached(title1)
            s2, ch2 = extract_number_cached(title2)
            
            if key1 and key2:
                if key1.find(key2) != -1 or key2.find(key1) != -1:
                    return True            
            elif ch1 and ch2 and ch1 == ch2:
                return True
            
            return False
        
        max_offset = 10
        index = 0
        src_length = len(src)
        for chapter in des:
            offset = 0
            while index + offset < src_length:
                if chapter_equal(src[index + offset]['title'], chapter['title']):
                    merge_chapter(chapter, src[index + offset])
                    index += offset + 1
                    break
                elif offset >= max_offset:
                    break
                offset += 1
        return des

class NovelRankModel(ContentModel):
    
    TYPE = "novel.novelrank"
    FIELDS = {
                "type" : u"",
                "novels" : [],
            }
    INDEXES = [
               {"key" : [("type", 1)], "unique" : True}
               ]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(NovelRankModel, self).__init__(dct, authority = authority)
                
    def find_dup(self):
        dup = self.collection().find_one({"type" : self["type"]})
        return self.wrap(dup)
    
    def get_novels(self, ids):
        items = NovelModel().find({"_id" : {'$in' : ids}})
        id2novel = {}
        for item in items:
            id2novel[item['_id']] = item
        novels = []
        for _id in ids:
            item = id2novel.get(_id)
            if item:
                novels.append(item)
        return novels            

    def on_import(self):
        ids = []
        for novel in self["novels"]:
            if is_uuid(novel):
                ids.append(novel)
            else:
                item = NovelModel().find_one({"title" : novel, "deleted" : False})
                if item:
                    ids.append(item["_id"])
        self['novels'] = ids    
        self._import()
            
    def export(self):
        dct = super(NovelRankModel, self).export()
        ids = dct["novels"]        
        dct["novels"] = [{"id" : item["_id"], "title" : item["title"], "visits" : item["visits"]} for item in self.get_novels(ids)]
        return dct


class NovelCMRankModel(ModelBase):
    TYPE = "novelcm.rank"
    FIELDS = {
              "type" : u"",
              "ids" : [], 
              }
    INDEXES = [
               {"key" : [("type", 1)], "unique" : True}
               ]
        
class NovelCMNovelModel(ModelBase):
    TYPE = "novelcm.novel"
    FIELDS = {
              "novel_id" : u"",
              "title" : u"", 
              "author" : u"",
              "tags" : [],
              "description" : u"",
              "category" : u"",
              "publisher" : u"",
              "publish_type" : u"",
              "price" : u"",
              "status" : u"",
              
              "c00" : u"",
              "c03" : u"",
              "c06" : u"",
              "c07" : u"",
              "c09" : u"",
              "c10" : u"",
              "c12" : u"",
              "c13" : u"",             
              "c15" : u"",                                          
              "c16" : u"",
              "c17" : u"",
              "c18" : u"",              
              "c20" : u"",
              "c21" : u"",
              "c22" : u"",
              "c23" : u"",
              "c24" : u"",
              "c26" : u"",
              "c27" : u"",
              "c29" : u"",
              "c30" : u"",
              }
    INDEXES = [{"key" : [("novel_id", 1)], "unique" : True}]


class NovelCMChapterModel(ModelBase):
    TYPE = "novelcm.chapter"
    FIELDS = {
              "novel_id" : u"",
              "chapter_id" : u"",
              "index" : 0,
              "title" : u"",
              "time" : datetime.utcfromtimestamp(0),
              "price" : 0,
              "words" : 0,
              "season_id" : u"",
              "season_title" : u"",
              }
    INDEXES = [
               {"key" : [("novel_id", 1), ("chapter_id", 1)], "unique" : True}
               ]

CATEGORY_MAP = {}

def load_maps():
    global CATEGORY_MAP
    
    basedir = os.path.dirname(__file__)
    CATEGORY_MAP = load_map(os.path.join(basedir, "map", "novel.category.map"))

def map_category(category, source):
    if source == "yqxw":
        return u"言情小说"
    if category.find(u"期刊") != -1:
        return u"期刊杂志"
    return CATEGORY_MAP.get(category)

def normalize_visits(visits, source):
    factors = {
                  "baidu" : 0.0, #no visits
                  "cm" : 1.0,
                  "unicom" : 0.0, #not accurate
                  "luoqiu" : 1.0, 
                  "shanwen" : 0.0, #no visits
                  "yqxw" : 0.0, #no visits
                  "duoku" : 0.0, #no visits
                  }
    visits = int(visits * factors.get(source, 0.0))
    if visits >= 100000000:
        visits = 99999999
    return visits

load_maps()
