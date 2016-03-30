#coding=utf8
from mktables import get_data
from django.template import Template, Context
from datetime import date, timedelta
from monitor_conf import  DAYS
from base64 import b64encode
from Template import HTML_ROW_UNIT, HTML_CONTENT
from monitor_conf import LOG_DATE

def get_image_code(image_path):
    with open(image_path,'rb') as f:
        return b64encode(f.read())
        
def get_recent_date(today, intervals):
    if not isinstance(today,date):
        raise TypeError
    intervals = int(intervals)
    date_list = []
    for interval in range(intervals):
        date_past = str(today+timedelta(days=-interval))
        date_list.append(date_past)
    return date_list

def str2date(date_str):#str='2013-12-28'
    lst = date_str.split('-')
    date_list = [int(x) for x in lst]
    return date(date_list[0],date_list[1],date_list[2])

#生成html替换列表
def get_data_source(param=None):
    today = date.today() if LOG_DATE is 'today' else str2date(LOG_DATE)
    date_list = get_recent_date(today,DAYS)
    data_source = []
    for current_date in date_list:
        data = get_data(current_date)
        if data:
            dct = data['total_info']        
            if param is None:
                data_source.append((dct['number'],dct['update'],dct['insert'],dct['error_num'],current_date))
            elif param  in ('number','update','insert','error_num'):
                data_source.append(dct[param])            
            elif param is 'date':
                data_source.append(current_date)
    return data_source

def get_html_data():
    sub_list = []
    for data in get_data_source():
        sub_list.append(HTML_ROW_UNIT % data)
    return sub_list
    
def get_html():
    t = Template(HTML_CONTENT)
    c = Context({'item_list':get_html_data()})
    return t.render(c)

if __name__=='__main__':
    get_html()