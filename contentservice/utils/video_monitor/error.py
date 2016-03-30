#coding=utf8
import subprocess, gzip
from datetime import date
from MonitorDataModel import ErrorSaveModel, ErrorInfoSaveModel
from monitor_conf import ERRORLOG_PATH, PREPROCESS_PATH, LOG_DATE

def process_output(output):
    #去除列表中每一项两边的空格和换行符
    output_copy = []
    for x in output:
        x = x.strip()
        output_copy.append(x)
    return output_copy

def get_log_name():#2013-12-28
    base_name = 'contentcrawler_error.log'
    if LOG_DATE is 'today':
        str_today = date.today().isoformat().replace('-','')
    else:
        str_today = LOG_DATE.replace('-', '')
    file_suffix = '.gz'
    file_name = base_name+'-'+str_today+file_suffix
    return file_name


PATH =  ERRORLOG_PATH+'%s'% get_log_name()
#错误信息分时统计
cmd1 = "grep -i '^ERROR' %s |awk -F' |\,|\(|\:' '{print $2','$10}' |sort|uniq -c|sort -n  -k 2 -k 1r -n" % PREPROCESS_PATH
#错误信息提取
cmd2 = "grep -i '^ERROR' %s |awk -F' Exception' '{print $2}'|sort|uniq -cd|sort -nr" % PREPROCESS_PATH 


def save_error():
    #读错误日志
    with  gzip.open(PATH,'r') as f:
        BUFFER = f.readlines()
        for line_number, line in enumerate(BUFFER):
            if line_number:
                if not line.startswith('ERROR') and  not line.startswith('WARNING'):
                    line = BUFFER[line_number-1].rstrip()
                    BUFFER[line_number -1] = line
        WRITE_BUFFER = BUFFER  
    #处理后的日志存放
    with open(PREPROCESS_PATH,'w+') as a:
        a.writelines(WRITE_BUFFER)    
    proc = subprocess.Popen(args=cmd1,shell=True,stdout=subprocess.PIPE)
    proc.wait()
    output1 = proc.stdout.readlines()
    output1 = process_output(output1)
    #output1示例['4948 06 novel.baidu.chapter', '3 06 video.tencent.list', '13 06 video.letv.album', '1 06 video.zy265.album']
    if LOG_DATE is 'today':
        ErrorSaveModel().delete_table(str(date.today()))
        ErrorSaveModel().delete_lastweek_table()
    else:
        ErrorSaveModel().delete_table(LOG_DATE)
    for item in output1:
        if item:
            ErrorSaveModel(item).save()
    #对具体错误信息的收集
    p1 = subprocess.Popen(args=cmd2,shell=True,stdout=subprocess.PIPE)
    output2 = p1.communicate()[0]
    output2 = output2.split('\n')
    output2 = process_output(output2)
    ErrorInfoSaveModel().delete_table(str(date.today()))
    ErrorInfoSaveModel().delete_lastweek_table()
    for item in output2:
        if item:
            ErrorInfoSaveModel(item).save()
    
    
    
    
if __name__=='__main__':
    save_error()  
    
    
    