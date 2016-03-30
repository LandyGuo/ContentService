'''
@author: Yu
'''
import time, sys, traceback
import mailutil, daemon
        
class ServiceDefinition(object):
    
    def __init__(self, check_func, name = "Service", check_interval = 180, retries = 3):
        if not callable(check_func):
            raise TypeError
        self.check_func = check_func
        self.name = name
        self.check_interval = check_interval
        self.retries = retries
        self.failures = 0
        self.last_check = None
        
    def check(self):
        self.check_func()
    

class ServiceException(Exception):
    def __init__(self, *args, **kwargs):
        super(ServiceException, self).__init__(*args, **kwargs)

class ServiceAlerter(object):

    def alert(self, title, content):
        raise NotImplemented

class ServiceMailAlerter(ServiceAlerter):

    def __init__(self, recipients, sender):
        self.recipients = recipients
        self.sender = sender
    
    def alert(self, title, content):
        try:
            mailutil.sendmail(title, self.recipients, self.sender, content)
        except:
            pass

class ServiceMonitor(object):
    
    def __init__(self, services = [], alerters = []):
        self.services = services
        self.alerters = alerters
    
    def run(self):
        while True:
            self.check()
            time.sleep(1)
    
    def check(self):
        for service in self.services:
            now = time.time()
            if (not service.last_check) or (now >= service.last_check + service.check_interval):
                try:
                    service.check()
                    if service.failures >= service.retries:
                        title = "SERVICE RECOVER - %s" % service.name
                        content = title
                        self.alert(title, content)
                    service.failures = 0 
                except Exception:
                    service.failures += 1
                    if service.failures >= service.retries:
                        title = "SERVICE FAILURE - %s" % service.name
                        content = get_exception_info()
                        self.alert(title, content)
                service.last_check = now
        
    def add_service(self, service):
        if not isinstance(service, ServiceDefinition):
            raise TypeError
        self.services.append(service)
    
    def add_alerter(self, alerter):
        if not isinstance(alerter, ServiceAlerter):
            raise TypeError
        self.alerters.append(alerter)
        
    def alert(self, title, content):
        for alerter in self.alerters:
            alerter.alert(title, content)
            
class ServiceMonitorDaemon(daemon.Daemon):
    def __init__(self, monitor, *args, **kwargs):
        if not isinstance(monitor, ServiceMonitor):
            raise TypeError
        self.monitor = monitor
        super(ServiceMonitorDaemon, self).__init__(*args, **kwargs)
        
    def run(self):
        self.monitor.run()
        
def get_exception_info():
    exc_type, value, tb = sys.exc_info()
    formatted_tb = traceback.format_tb(tb)
    data = 'Exception %s: %s traceback=%s' % (exc_type, value, formatted_tb)
    return data