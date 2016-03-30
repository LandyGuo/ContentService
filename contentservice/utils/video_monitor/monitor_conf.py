#coding=utf8

'''                              fix ip  and log path here              '''
_MONGO_CONN_STR ='mongodb://10.200.20.60:27017'
LOG_PATH = '/var/app/log/contentservice/'
# _MONGO_CONN_STR ='mongodb://localhost:27017'
# LOG_PATH = '/home/guo/e/'
LOG_DATE = 'today'#or format str '2013-12-28'
LOG_SAVE_PATH = '/home/guo/preprocess.log'
TABLE_SAVE_PATH = '/home/guo/statistics.xlsx'
#error 
ERRORLOG_PATH = LOG_PATH
PREPROCESS_PATH = LOG_SAVE_PATH
#出现次数多于此阈值的错误将在邮件报表显示
THRESHOLD = 50
#数据在数据库中保存时间
TIME_DELTA = -7
#update
INSERT_PATH = LOG_PATH
SKIP_PATH = LOG_PATH
UPDATE_PATH = LOG_PATH
#url_sheet_data
FILE_PATH = TABLE_SAVE_PATH
#邮件上显示历史数据的天数
DAYS = 30
#邮件显示统计图片的位置和大小
IMAGE_PATH = '/home/guo/pic1.jpg'
DPI = 80
#email
EMAIL_HOST = 'smtp.qq.com'  
HOST_PORT = 25  
EMAIL_USER_NAME ='crawlerreport@qq.com'  
EMAIL_PASSWORD = 'Bainacompany' 
FROM_ADDRESS = EMAIL_USER_NAME  
'''                              fix to_address here                      '''
TO_ADDRESS = ['KLi@bainainfo.com','lxwu@bainainfo.com','rli@bainainfo.com',
              'zhhfang@bainainfo.com','yluo@bainainfo.com','qpguo@bainainfo.com']



