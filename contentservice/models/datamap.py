# -*- coding: utf-8 -*-
'''
Created on Nov 21, 2013

@author: lxwu
'''
import os
import re
from common import load_map

CHANNEL_DICT = {
                    u"动漫" : u"animate",
                    u"电影" : u"film",
                    u"热点" : u"hot",
                    u"搞笑" : u"joke",
                    u"电视剧" : u"tv",
                    u"综艺" : u"variety",
                    u"福利" : u"welfare",
                    }

MAP_DICT = {}

def tag_mapping(source, channel, tags):
    categories = []
    region = ""
    for item in tags:
        new_item = map_tag(source, channel, item)
        try:
            category = re.findall("(.+)_categories", new_item)[0]
            categories.append(category)
        except:
            if new_item != u"其它":
                region = re.findall("(.+)_region", new_item)[0]
    item_dict = {
                 "categories": categories,
                 "region": region
                 }
    return item_dict
        
def map_channel(channel):
    map = MAP_DICT.get("video_channel_map")
    return map.get(channel, u"其它")

def map_classification(channel, classification, map_item):
    if channel == u"其它":
        return u"其它"
    channel = CHANNEL_DICT.get(channel)
    map = MAP_DICT.get('video_%s_%s_map' % (channel, classification))
    return map.get(map_item, u"其它")

def map_tag(source, channel, item):
    if channel == u"其它":
        return u"其它"
    channel = CHANNEL_DICT.get(channel)
    map = MAP_DICT.get('video_%s_%s_map' % (source, channel))
    return map.get(item, u"其它")

def load_maps():
    basedir = os.path.dirname(__file__)
    path = os.path.join(basedir, "map")
    dir_list = os.listdir(path)
    for dir in dir_list:
        file_path = os.path.join(path, dir)
        if os.path.isfile(file_path):
            MAP_DICT[dir.replace(".", "_")] = load_map(file_path)
    
load_maps()