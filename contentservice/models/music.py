#coding=utf8
from datetime import datetime
from base import ContentModel

SOURCE_AUTHORITY = {
                    "baidu" : 8,
                    "qq" : 7,
                    "xiami" : 6,
                    }

class MusicModel(ContentModel):
    
    TYPE = "music.song"
    FIELDS =  {
                 "artist" : u"",
                 "album" : u"",
                 "duration" : 0,
                 "lyrics" : u"",
                 "language" : u"",
                 "genres" : u"",
                 }
    INDEXES = [
               {"key" : [("title", 1)]},
               {"key" : [("artist", 1)]},
               {"key" : [("album", 1)]},
               ]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(MusicModel, self).__init__(dct, authority = authority)
                
    def find_dup(self):
        dup = self.collection().find_one({"title" : self["title"], "artist" : self["artist"]})
        return self.wrap(dup)


class MusicAlbumModel(ContentModel):
    
    TYPE = "music.album"
    FIELDS = {
             "artist" : u"",
             "duration" : 0,
             "language" : u"",
             "genres" : u"",
             }
    INDEXES = [{"key" : [("title", 1)]},
               {"key" : [("artist", 1)]}]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(MusicAlbumModel, self).__init__(dct, authority = authority)
        
    def find_dup(self):
        dup = self.collection().find_one({"title" : self["title"], "artist" : self["artist"]})
        return self.wrap(dup)

    
class MusicArtistModel(ContentModel):
    
    TYPE = "music.artist"
    FIELDS = {
             "region" : u"",
             "birthday" : datetime.utcfromtimestamp(0),
             "gender" : 0,
             }
    INDEXES = [{"key" : [("title", 1)]}]

    def __init__(self, dct = {}, authority = None):
        if authority is None:
            authority = SOURCE_AUTHORITY.get(dct.get('source'))
        super(MusicArtistModel, self).__init__(dct, authority = authority)
                
    def find_dup(self):
        dup = self.collection().find_one({"title" : self["title"]})
        return self.wrap(dup)