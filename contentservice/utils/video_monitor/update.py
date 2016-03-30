#coding=utf8
from MonitorDataModel import StateInfoModel
from datetime import datetime, date
from monitor_conf import INSERT_PATH, SKIP_PATH, UPDATE_PATH, LOG_DATE
import  subprocess  

def process_output(output):
    #去除列表中每一项两边的空格和换行符
    output_copy = []
    for x in output:
        x = x.strip()
        output_copy.append(x)
    return output_copy

def get_isotime(items):
    year, month, day = items[0].split('-')
    hour, minute = items[1:3]
    second, microsecond = items[-1].split('.')
    year =year.lstrip('\'')
    microsecond = microsecond.rstrip('\'')
    isotime =  datetime(int(year),int(month),int(day),int(hour),int(minute),int(second),int(microsecond))
    return isotime
    
def clean(to_clean_list):
    if isinstance(to_clean_list,str):
        return to_clean_list.strip('\'')
    if isinstance(to_clean_list,list):
        lst = []
        for item in to_clean_list:
            lst.append(item.strip('\''))
        return lst   
    
def Create_Process(cmd_root,path,*args):
    p1 = subprocess.Popen(args=cmd_root % path,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    out_last = p1.communicate()[0]
    output = None
    count = len(args)
    for i in range(count):
        if output:
            out_last = output
        cmd = args[i]
        process = subprocess.Popen(args=cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        output = process.communicate(input=out_last)[0]
    return output
#inserted_video.log-20131223.gz
def get_log_name(base_name):
    base_suffix = '.log'
    if LOG_DATE is 'today':
        today = date.today().isoformat().replace('-','')
    else:
        today = LOG_DATE.replace('-', '')
    file_suffix = '.gz'
    file_name = base_name+base_suffix+'-'+today+file_suffix
    return file_name


INSERT_LOG_PATH =INSERT_PATH + "%s" % get_log_name('inserted_video')
SKIP_LOG_PATH = SKIP_PATH+"%s" % get_log_name('skipped_video')
UPDATE_LOG_PATH = UPDATE_PATH+"%s" % get_log_name('updated_video')


CMD_ROOT = "zcat %s|grep 'INFO' "
CMD1 = "awk -F'\{|\}' '{print $2}'"
#1
CMD2 = "awk -F':|,' '{print $2','$4','$6','$8','$9','$10','$12}'"
#2
CMD3 = "awk -F':|,' '{print $2','$4','$12}'"
CMD4 = '''awk -F"\'" '{print $2','$4','$6}'|sort|uniq -c|sort -nr'''

def save_update():
    '''存储新增和更新的记录'''
    model = StateInfoModel()
    if LOG_DATE is 'today':
        model.delete_lastweek_table()
        model.delete_table(str(date.today()))
    else:
        model.delete_table(LOG_DATE)
    for process_path in (INSERT_LOG_PATH,UPDATE_LOG_PATH): 
        output = Create_Process(CMD_ROOT,process_path,CMD1,CMD2)
        output = process_output(output.split('\n'))#output为列表
        for x in output:
            items = x.split()
            if items:
                source, channel, album_id = clean(items[0:3])
                log_type = clean(items[-1])
                time_list = clean(items[-5:-1])
                hour = int(time_list[1])
                isotime = get_isotime(time_list)
#                 print "source:%s channel:%s album_id:%s time:%s log_type:%s" %(source,channel,album_id,isotime,log_type)
                data = model.InitModel(source, channel, album_id, isotime, hour, log_type)
                StateInfoModel(data).save()
    '''
    #对于skip的log单独处理,仅记录其类型和数目
    output = Create_Process(CMD_ROOT,SKIP_LOG_PATH,CMD1,CMD3,CMD4)
    #output为输出文件流
    output = process_output(output.split('\n'))
    for x in output:
        if x:
            number, source, channel, log_type = x.split()
#             print 'number:%s source:%s channel:%s log_type:%s'%(number,source,channel,log_type) 
            data = model.InitModel(source=source,channel=channel,number=number,log_type=log_type)
            StateInfoModel(data).save()
    '''
    
if __name__=='__main__':
    save_update()          
            
        
    
    
    
    