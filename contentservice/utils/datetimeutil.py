# -*- coding: utf-8 -*-
import calendar
from datetime import datetime

def unix_time(dt = datetime.utcnow()):
    return calendar.timegm(dt.utctimetuple())

def parse_date(text, formats = []):
    if not text:
        return None
    if not formats:
        formats = [u"%Y-%m-%d", u"%Y-%m", u"%Y", u"%Y年%m月%d日", u"%Y年%m月", u"%Y年"]          
    for f in formats:                       
        try:
            dt = datetime.strptime(text.strip().encode('utf8'), f.encode('utf8'))
            return dt         
        except:
            pass