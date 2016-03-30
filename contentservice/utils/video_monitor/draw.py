#coding=utf8
import matplotlib
matplotlib.use('Agg')
from matplotlib import pylab as pl
from datetime import datetime, timedelta
from url_sheet_data import get_data_source
from matplotlib.dates import DateFormatter
from monitor_conf import IMAGE_PATH, DPI, LOG_DATE


def str2datetime(date_str):#str='2013-12-28'
    lst = date_str.split('-')
    date_list = [int(x) for x in lst]
    return datetime(date_list[0],date_list[1],date_list[2])

def draw():
    #获取时间轴
    date_num = len(get_data_source('date'))
    today = datetime.today() if LOG_DATE is 'today' else str2datetime(LOG_DATE)
    x_time =[today+timedelta(-i) for i in range(date_num)] 
    dates = pl.date2num(x_time)
    #创建图1
    pl.figure(1)
    #子图1
    ax1 = pl.subplot(2,2,1)    
    update_list = get_data_source('number')
    ax1.plot_date(dates,  update_list,  'r-',  marker='.',  linewidth=1)
    ax1.xaxis.set_major_formatter( DateFormatter('%m.%d'))
    pl.xlabel('date')
    pl.ylabel('album number')
    pl.title('the number of album db')
    #子图2
    ax2 = pl.subplot(2,2,2)
    insert_list = get_data_source('insert')
    ax2.plot_date(dates,  insert_list,  'b-',  marker='*',  linewidth=1)
    ax2.xaxis.set_major_formatter( DateFormatter('%m.%d') )
    pl.xlabel('date')
    pl.ylabel('increasement')
    pl.title('daily album increasement')
    #子图3
    ax3 = pl.subplot(2,2,3)
    err_num_list = get_data_source('error_num')
    ax3.plot_date(dates,  err_num_list,  'y-',  marker='+',  linewidth=1)
    ax3.xaxis.set_major_formatter( DateFormatter('%m.%d') )
    pl.xlabel('date')
    pl.ylabel('error')
    pl.title('occurred errors')
    #子图4
    ax4 = pl.subplot(2,2,4)
    err_num_list = get_data_source('update')
    ax4.plot_date(dates,  err_num_list,  'g-',  marker='^',  linewidth=1)
    ax4.xaxis.set_major_formatter( DateFormatter('%m.%d') )
    pl.xlabel('date')
    pl.ylabel('update')
    pl.title('updated albums')
    
    pl.figure(1).autofmt_xdate()
    pl.figure(1).tight_layout()
    pl.savefig(IMAGE_PATH,dpi=DPI)
    
#     pl.show()
    
if __name__=='__main__':
    draw()