'''
E2E monitor service

@author: Yu
'''
from utils.monitor import ServiceDefinition, ServiceMonitor, ServiceMailAlerter, ServiceMonitorDaemon
import requests
from settings import RING_SERVER

EMAIL_TO = ["yxia@bainainfo.com", "yyu@bainainfo.com"]
MONITOR_SERVICE_PID = "/var/run/contentservice_monitor.pid"

def api_ring(path, params = {}):
    if not path.startswith("/"):
        path = "/" + path
    url = "http://" + RING_SERVER + path
    resp = requests.get(url, params = params)
    resp.raise_for_status()
    return resp.json()

def ring_e2e():
    data = api_ring("/api/ring/startup_info")
    assert data
    
    data = api_ring("/api/ring/scene_rank", {"carrier" : "cm", "type" : "default"})
    assert data["items"]
    
    data = api_ring("/api/ring/ring_ranklist", {"carrier" : "cm"})
    assert data["items"]
    
    data = api_ring("/api/ring/ringtone_rank", {"carrier" : "cm", "type" : "hot"})
    assert data["items"]
    

def service(command):
    monitor = ServiceMonitor()
    monitor.add_service(ServiceDefinition(ring_e2e, "ring service"))
    monitor.add_alerter(ServiceMailAlerter(recipients = EMAIL_TO, sender = "content service"))
    
    daemon = ServiceMonitorDaemon(monitor, pidfile = MONITOR_SERVICE_PID)
    if command == "start":
        daemon.start()
    elif command == "stop":
        daemon.stop()
    elif command == "restart":
        daemon.restart()
    elif command == "status":
        daemon.status()


if __name__ == "__main__":
    ring_e2e()
