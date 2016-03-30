# -*- coding: utf-8 -*-
from datetime import datetime
from time import mktime
from hashlib import md5
import re, traceback, sys

def get_exception_info():
    exc_type, value, tb = sys.exc_info()
    formatted_tb = traceback.format_tb(tb)
    data = 'Exception %s: %s Traceback=\n%s' % (exc_type, value, ''.join(formatted_tb))
    return data

def md5digest(string):
    return md5(string.encode('utf-8')).hexdigest()

def get_ip_address(ifname='eth0'):
    import socket
    import fcntl
    import struct
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ipaddr = socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
    return ipaddr

def exception_handled(logger, retvalue_on_error = None):
    def _decorator(func):
        def _view(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.error(get_exception_info())
                return retvalue_on_error
        return _view
    return _decorator
