# -*- coding: utf-8 -*-
import re
from text import extract_key

_CHAR2NUM = {
             u"0" : 0,
             u"1" : 1,
             u"2" : 2,
             u"3" : 3,
             u"4" : 4,
             u"5" : 5,
             u"6" : 6,
             u"7" : 7,
             u"8" : 8,
             u"9" : 9,
             u"零" : 0,
             u"一" : 1,
             u"壹" : 1,
             u"二" : 2,
             u"贰" : 2,
             u"两" : 2,
             u"三" : 3,
             u"叁" : 3,
             u"四" : 4,
             u"肆" : 4,
             u"五" : 5,
             u"伍" : 5,
             u"六" : 6,
             u"陆" : 6,
             u"七" : 7,
             u"柒" : 7,
             u"八" : 8,
             u"捌" : 8,
             u"九" : 9,
             u"玖" : 9,
             u"十" : 10,
             u"拾" : 10,
             u"百" : 100,
             u"佰" : 100,
             u"千" : 1000,
             u"仟" : 1000,
             u"万" : 10000,
             u"亿" : 100000000,
             }

def extract_chapter_number(text):
    '''
    returns (season, chapter)
    '''
    season = 0
    chapter = 0
    if not text:
        return season, chapter
    
    num_texts = "".join(_CHAR2NUM.keys())
    texts = re.findall(u"([%s]+)[章节]" % num_texts, text)
    if texts:
        chapter = parse_number(texts[0])
    
    texts = re.findall(u"([%s]+)[篇卷部]" % num_texts, text)
    if texts:
        season = parse_number(texts[0])
    
    if not (season or chapter):
        texts = re.findall(u"([%s]+)[\s:]" % num_texts, text)
        if len(texts) == 1:
            chapter = parse_number(texts[0])
    
    
    return season, chapter

def extract_chapter_key(text):
    keys = []
    for key in extract_key(text).split(" "):
        #remove words with "章节"
        season, chapter = extract_chapter_number(key)
        if not (season or chapter):
            keys.append(key)         
    return " ".join(keys)

def parse_number(text):
    assert isinstance(text, basestring)
    
    if isinstance(text, str):
        text = unicode(text, 'utf8')
    if text.isdigit():
        return int(text)
    
    total = 0
    last_number = None
    for c in text:
        n = _CHAR2NUM[c]
        if last_number is not None:
            if n >= 10:
                total += last_number * n
                last_number = None
            else:
                last_number = last_number * 10 + n
        else:
            if n >= 10:
                total *= n
                if total == 0 and n == 10:
                    total = 10
            else:
                last_number = n
    if last_number is not None:
        total += last_number
    return total 
    
if __name__ == "__main__":
    tests = [
                (u"壹", 1), (u"十五", 15), (u"三十八", 38), 
                (u"八十", 80), (u"一百零三", 103), (u"五百五十", 550),
                (u"三千", 3000), (u"五千零三十七", 5037),
                (u"三万四千五百六十七", 34567), (u"一百万", 1000000),
                (u"三十万四千亿", 30400000000000),
                (u"五四三二", 5432),
            ]
    for text, num in tests:
        assert parse_number(text) == num
    
    print extract_chapter_number(u"第二卷 第一百二十章 哈哈哈")
    print extract_chapter_key(u"第十章 《阵法九卷》")
    
    