#coding=utf8
from pymongo import MongoClient, collection
from datetime import date
from MonitorDataModel import MonitorDataModel, ErrorInfoSaveModel
from monitor_conf import _MONGO_CONN_STR, THRESHOLD, LOG_DATE
 
def get_num(collect,channel=None,source=None,log_type=None):
    today = str(date.today())
    query = {}
    query['updatetime'] = today if LOG_DATE is 'today' else LOG_DATE
    if not isinstance(collect,collection.Collection):
        return None
    if channel:
        query['channel'] = channel
    if source:
        query['source'] = source
    if log_type:
        query['log_type'] = log_type
    return collect.find(query).count()
 

def save_db():
    data = MonitorDataModel().InitModel()
    client =  MongoClient(_MONGO_CONN_STR)
    db = client['video_monitor']
    collect = db['state_info']
    for log_type in ('insert', 'update', 'skip'):
        for channel in data['channel_list']:
            data['channel_info'][channel][log_type] = get_num(collect,channel=channel,log_type=log_type)
            for source in data['source_list']:
                data['source_detail'][source][channel][log_type] = get_num(collect,channel,source,log_type) 
        for source in data['source_list']:
            num = get_num(collect,source=source,log_type=log_type)
            data['source_info'][source][log_type] = num
#             print "source:%s  log_type:%s  num:%s" % (source, log_type, num)
        data['total_info'][log_type] = get_num(collect, log_type=log_type)    
    data['total_info']['error_num'] = len(ErrorInfoSaveModel().get_data(LOG_DATE,THRESHOLD))
    MonitorDataModel(data).save()

if __name__=='__main__': 
    save_db()