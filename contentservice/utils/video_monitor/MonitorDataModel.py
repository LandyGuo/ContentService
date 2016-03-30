#coding=utf8
from pymongo import MongoClient
from datetime import datetime, date, timedelta
from contentservice.utils.typeutil import convert
from monitor_conf import _MONGO_CONN_STR, TIME_DELTA, LOG_DATE
import re, copy

_COLLECTIONS = {} 




class MonitorDataModel(dict):
    
    type = 'video.monitor.statistics'
    
    FIELDS= {
                    'updatetime': date.today().isoformat() if LOG_DATE is 'today' else LOG_DATE,
                    'total_info': {},#'number':0,'updated':0,'skip':0,'insert':0
                    'channel_list': [],
                    'channel_info': {},#{u'电影':0,u'电视剧':0,u'综艺':0,u'动漫':0,u'热点':0,u'搞笑':0,u'其它':0}
                    'source_list': [],
                    'source_info': {},
                    'source_detail': {},#{'bdzy':INNER_FIELDS1}
            }#数据存储结构
    
    INNER_FIELDS1= {
                    u'电影': {},#{INNER_FIELDS2}
                    u'电视剧': {}, 
                    u'综艺': {},
                    u'动漫': {},
                    u'热点': {},
                    u'搞笑': {},
                    u'其它': {},
                    u'福利': {},
                    u'音乐': {},
                    u'恐怖': {},
                    u'擦边': {},
                    u'未映射': {},
                   }
    
    INNER_FIELDS2= {'number': 0,'update': 0,'insert': 0,'skip': 0}
    
    def __init__(self, dct={}):
        if not isinstance(dct, dict):
            raise TypeError
        for key in self.FIELDS.keys():
            self[key] = dct.get(key)
                
    def __setitem__(self, key, value):
        if key not in self.FIELDS:
            return 
        t = type(self.FIELDS[key])
        if value is None:
            value = copy.deepcopy(self.FIELDS[key])
        elif not isinstance(value, t):
            value = convert(value, t)
            if value is None:
                raise TypeError
        super(MonitorDataModel, self).__setitem__(key, value)
                
    def InitModel(self):#初始化一个含有统计数据库各个数据来源的表
        dct = self.FIELDS     
        sources = self.GetDataCollection().distinct('source')
        channels = self.GetDataCollection().distinct('channel')
        channels = self.del_null(channels)
        sources = self.del_null(sources)
        dct['source_list'] = sources
        dct['channel_list'] = channels
        dct['total_info']['number'] = self.GetDataCollection().count()
        for source in sources:
            dct['source_detail'][source] = {}
            dct['source_info'][source] = {'number':self.get_num(source)}
            for channel in channels:
                dct['source_detail'][source][channel] = {'number':self.get_num(source,channel)} 
        for channel in channels:    
            dct['channel_info'][channel] = {'number':self.get_num(channel=channel)}
        dct['channel_info'][u'未映射'] = {'number': get_unmap(dct, channels)}
        return dct
    
    def del_null(self,lst):
        lst_copy = lst[:]
        for x in lst_copy:
            if x=='':
                lst.remove(x)
        return lst
                          
    def _collection(self):#获得存统计数据的数据库
        if not _COLLECTIONS.get(self.type):
            client = MongoClient(_MONGO_CONN_STR)
            [base, db_name, collection_name] = self.type.split('.')[:]
            collection = client[base + '_' + db_name][collection_name]  
            _COLLECTIONS[self.type] = collection
        return _COLLECTIONS[self.type]       
    
    def GetDataCollection(self):#获得数据来源的数据库
        client = MongoClient(_MONGO_CONN_STR)       
        collection = client['content_video']['video.album']
        return collection
           
    def get_num(self,source=None,channel=None):#query
        query = {}
        if source:
            query['source'] = source
        if channel:
            query['channel'] = channel
        return self.GetDataCollection().find(query).count() 
                   
    def findOne(self,query={}):#同一天只存一张表，同一天内后存的表覆盖先前的表
        return  self._collection().find_one(query)
                      
    def save(self):        
        query = {'updatetime':self.get('updatetime')}
        if self.find_dup(query):
            self._collection().update(query, self, upsert = True)
        else:
            self._collection().save(self)
 
    def find_dup(self,query):
        return self.findOne(query=query)
    
    def find_table(self,querydate):#根据日期从存储数据库中找一张表2013-12-10
        query = {}
        query['updatetime'] = querydate
        data = self.findOne(query)
        return data if data else None
    
    def delete_lastweek_table(self):
        today = date.today()
        last_today = today+timedelta(days=TIME_DELTA)
        self.delete_table(str(last_today))
        
    def delete_table(self,date_str):
        if not isinstance(date_str, str):
            raise TypeError
        query = {}
        query['updatetime'] = date_str
        self._collection().remove(query)
        

class ErrorSaveModel(MonitorDataModel):
    
    type = "video.monitor.error"
    
    FIELDS = {
              'updatetime': date.today().isoformat() if LOG_DATE is 'today' else LOG_DATE,
              'error_hour': 0,
              'error_source': '',#'video.bdzy.novel
              'error_number': 0,#
             }

    def __init__(self,item=""):
        if not isinstance(item,str):
            raise TypeError
        model = self.InitModel(item)
        if model:
            for key in self.FIELDS:
                self[key] = model[key]
            
    def InitModel(self,item):
        if not item:
            return None
        model = self.FIELDS
        error_number,error_hour,source = item.split()
        model['error_number'] = int(error_number)
        model['error_hour'] = int(error_hour)
        model['error_source'] = source   
        return model
    
    def find(self,querydate):
        if not isinstance(querydate, str):
            raise TypeError
        query = {}
        query['updatetime'] = querydate
        cursor = self._collection().find(query)
        if cursor:
            lst = []
            for item in cursor:
                lst.append(item)
            return lst
        else:
            return None
        
    def get_error_element(self,querydate,query_type):
        if not isinstance(querydate, str):
            raise TypeError
        if query_type not in ('source', 'hour'):
            raise TypeError
        query = {}
        query['updatetime'] = querydate
        lst = self._collection().find(query).distinct('error_%s' % query_type)
        lst.sort()
        return lst if lst else None
    
    def get_num(self,querydate,error_source='',error_hour=''):
        query = {}
        query['updatetime'] = querydate
        if error_source:
            query['error_source'] = error_source
        if error_hour:
            query['error_hour'] = int(error_hour)
        result = self._collection().find_one(query)
        return result['error_number'] if result else 0
            
    def save(self):
        self._collection().save(self) 
    

class ErrorInfoSaveModel(ErrorSaveModel):
    
    type = 'video.monitor.err_info'
    
    FIELDS = {
              'updatetime': date.today().isoformat() if LOG_DATE is 'today' else LOG_DATE,
              'err_num': 0,
              'err_type': '',
              'err_info': '',
              'err_location': '',
              }
    
    def __init__(self,item=''):
        super(ErrorInfoSaveModel,self).__init__(item)
    
    def InitModel(self,item):
        if not item:
            return None
        model = self.FIELDS
        try:
            model['err_num'] = int(re.findall(u'(\d+) ',item)[0])
            model['err_type'] = re.findall(r'<(.+)>',item)[0]
            model['err_info'] = re.findall(r'>:(.+)Traceback',item)[0]
            model['err_location'] = re.findall(r'Traceback=(.+)',item)[0]
        except IndexError:
            pass
        return model
    
    def get_data(self,query_date,threshold):#those errors whose err_num are greater than threshold would be return  
        query = {}
        if query_date is 'today':
            query_date = date.today().isoformat()
        query['updatetime'] = query_date
        query['err_num'] = {'$gt':threshold}
        items = self._collection().find(query)
        if items:
            result = []
            for item in items:
                result.append(item)
            return result
        else:
            return None
        
            
class StateInfoModel(MonitorDataModel):
    
    type = "video.monitor.state_info"
    
    FIELDS = {
              'updatetime': date.today().isoformat() if LOG_DATE is 'today' else LOG_DATE,
              'source': '',
              'channel': '',
              'album_id': '',
              'hour': 0,
              'isotime': datetime.utcnow(),
              'log_type': '',
              'number': 0,
              }
    
    def __init__(self,dct={}):
        if not isinstance(dct, dict):
            raise TypeError
        for key in self.FIELDS.keys():
            value = dct.get(key)
            self[key] = self.clean(value)if isinstance(value, str) else value
  
    def InitModel(self, source='', channel='', album_id='', time=datetime.utcnow(), hour=0, log_type='',number=0):
        items = [('source',source),('channel',channel),('album_id',album_id),
                 ('isotime',time),('hour',hour),('log_type',log_type),('number',number)]
        model = dict(items)
        model['updatetime'] = date.today().isoformat() if LOG_DATE is 'today' else LOG_DATE
        return model
    
    def get_num(self,log_type,source,hour,querydate):
        query = {}
        query['updatetime'] = querydate
        if log_type:
            query['log_type'] = log_type
        if source:
            query['source'] = source
        if hour:
            query['hour'] = hour
        return self._collection().find(query).count()
    
    def get_state_distinct(self,query_info,querydate):
        query = {}
        query['updatetime'] = querydate
        if query_info not in ('hour', 'source'):
            raise TypeError
        result = self._collection().find(query).distinct(query_info)
        if query_info=='hour':
            result.sort()
        return result
        
    def save(self):
        self._collection().save(self)
        
    def clean(self,item):
        return item.strip()
        
    
def get_unmap(data,channels):
    total = 0 
    for channel in channels:
        number = data['channel_info'][channel].get('number',0) 
        total+=number
    return data['total_info']['number']-total       
           

'''数据存储模型
     
    data={
            'updatetime': str(date.today()),
            'channel_list':[u'电影',u'电视剧',u'综艺',u'动漫',u'热点',u'搞笑',u'其它'],
            'channel_info':{u'电影':{'number':0,'update':0,'insert':0,'skip':0},
                            u'电视剧':{'number':0,'update':0,'insert':0,'skip':0},
                            u'综艺':{'number':0,'update':0,'insert':0,'skip':0},
                            u'动漫':{'number':0,'update':0,'insert':0,'skip':0},
                            u'热点':{'number':0,'update':0,'insert':0,'skip':0},
                            u'搞笑':{'number':0,'update':0,'insert':0,'skip':0},
                            u'其它':{'number':0,'update':0,'insert':0,'skip':0},}
            'source_list':['bdzy','qvod','360'],
            'source_detail': {
                            'baidu':{
                                        u'电影': {'number':0,'update':0,'insert':0,'skip':0},
                                        u'电视剧': {'number':0,'update':0,'insert':0,'skip':0}, 
                                        u'综艺': {'number':0,'update':0,'insert':0,'skip':0},
                                        u'动漫': {'number':0,'udpate':0,'insert':0,'skip':0},
                                        u'热点': {'number':0,'update':0,'insert':0,'skip':0},
                                        u'搞笑': {'number':0,'update':0,'insert':0,'skip':0},
                                        u'其它': {'number':0,'update':0,'insert':0,'skip':0},
                                   },
                            },
            'source_info': {
                           'baidu':{'number':0,'updated':0,'skip':0,'insert':0},
                           'qvod':{'number':0,'updated':0,'skip':0,'insert':0},
                           },
            'total_info':{'number':0,updated':0,'skip':0,'insert':0}
          }
'''                
            

    

