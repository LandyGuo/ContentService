#coding=utf8
import smtplib  
from email.mime.text import MIMEText 
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.Header import Header
from url_sheet_data import get_html
from datetime import date
from monitor_conf import TABLE_SAVE_PATH ,EMAIL_USER_NAME, IMAGE_PATH, \
                EMAIL_PASSWORD ,FROM_ADDRESS  ,TO_ADDRESS ,EMAIL_HOST ,HOST_PORT  
  

def send_email():
    mail_username = EMAIL_USER_NAME
    mail_password = EMAIL_PASSWORD  
    from_addr = FROM_ADDRESS 
    to_addrs = TO_ADDRESS  
    #html_content
    send_html = get_html()
    # HOST & PORT  
    HOST = EMAIL_HOST  
    PORT = HOST_PORT
    # Create SMTP Object  
    smtp = smtplib.SMTP()  
    smtp.connect(HOST,PORT)  
    smtp.login(mail_username,mail_password)   
    msgRoot = MIMEMultipart('related')
    msg1 = MIMEText(send_html,'html','utf-8') 
    with open(IMAGE_PATH,'rb') as f:
        msg2 = MIMEImage(f.read())
        msg2['Content-Disposition'] = 'inline;filename="image.jpg"'
        msg2.add_header('Content-ID', '<image1>')    
    with open(TABLE_SAVE_PATH,'rb') as f:
        msg3 = MIMEText(f.read(),'base64','gb2312') 
        msg3["Content-Type"] = 'application'
        msg3["Content-Disposition"] = 'attachment;filename="爬虫库资源详情.xlsx"'
    msgRoot.attach(msg1) 
    msgRoot.attach(msg2)
    msgRoot.attach(msg3)
    msgRoot['From'] = from_addr
    msgRoot['To'] = ';'.join(to_addrs)
    msgRoot['Subject']= Header('爬虫库状态通知邮件(' + str(date.today()) + ')','utf-8') 
    smtp.sendmail(from_addr,to_addrs,msgRoot.as_string())  
    smtp.quit() 
if __name__=='__main__':
    send_email() 