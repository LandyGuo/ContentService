#coding=utf8
import error, update,db_data, mktables, send_email, draw
from mktables import TODAY

def run():
    print 'date:%s step1 start error statistics' % TODAY
    error.save_error()
    print 'date:%s step2 start update statistics' % TODAY
    update.save_update()
    print 'date:%s step3 start db statistics' % TODAY
    db_data.save_db()
    print 'date:%s step4 start making tables' % TODAY
    mktables.mktables()
    print 'date:%s step5 start draw statistics picture' % TODAY
    draw.draw()
    print 'date:%s step6 start sending emails' % TODAY
    send_email.send_email()
    print 'date:%s finished' % TODAY
    
    
if __name__=='__main__':
    run() 