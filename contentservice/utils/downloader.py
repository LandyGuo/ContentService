import urllib3, urlparse, urllib, time
from scrapy.selector import HtmlXPathSelector
from datetimeutil import unix_time
import random

_SITES_RATE_LIMIT = {
              "mp3.easou.com" : 1.0,
              'music.douban.com' : 2.0,   
              'douban.fm' : 2.0,   
              'music.baidu.com' : 2.0,               
              }

_SITES_LAST_ACCESS = {}

_NUM_POOLS = 10
_TIMEOUT = 30
_DEFAULT_HEADER = {}
#_DEFAULT_HEADER =  {
#        'Accept' :"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#        'Accept-Charset' : "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
#        'Accept-Encoding' : "gzip,deflate,sdch",
#        'Accept-Language' : "en-US,en;q=0.8",
#        'Cache-Control' : 'max-age=0',
#        'Connection' :'keep-alive',
#        'User-Agent' :"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.162 Safari/535.19"
#    } 

_HTTP = urllib3.PoolManager(num_pools = _NUM_POOLS, timeout = _TIMEOUT)
_PROXY = {}


class Response(object):
    def __init__(self, status = 200, body = None, headers = {}):
        self.status = status
        self.body = body
        self.headers = headers

class DownloadException(Exception):
    def __init__(self, status):
        self.status = status        
    def __str__(self):
        return "Status = %s" % self.status
        
def download(url, method = "GET", params = {}, body = None, headers = {}, proxys = []):    
    if not url:
        raise DownloadException("Url is None")
    
    if isinstance(url, unicode):
        url = url.encode('utf8')
    for k, v in params.iteritems():
        if isinstance(v, unicode):
            params[k] = v.encode('utf8')    
    
    if params:
        if method == "GET" and url.find('?') == -1:            
            url = url + "?" + urllib.urlencode(params)
        elif method == "POST":
            body = urllib.urlencode(params)
    
    parse = urlparse.urlparse(url)        
    site = parse.netloc
        
    if _SITES_RATE_LIMIT.has_key(site):
        global _SITES_LAST_ACCESS
        last_visit = _SITES_LAST_ACCESS.get(site)
        now = unix_time()        
        if last_visit:
            waittime = last_visit + _SITES_RATE_LIMIT[site] - now
            if waittime > 0:
                time.sleep(waittime)
        _SITES_LAST_ACCESS[site] = now                
    
    
    proxy = proxys[random.randint(0, len(proxys) - 1)] if proxys else None

    pool = _HTTP
    if proxy:        
        if not _PROXY.has_key(proxy):
            _PROXY[proxy] = urllib3.proxy_from_url(proxy)
        pool = _PROXY[proxy]
    _headers = _DEFAULT_HEADER
    _headers["Host"] = parse.netloc
    for k, v in headers.iteritems():
        if not v and _headers.has_key(k):
            _headers.pop(k)
        else:
            _headers[k] = v    

    resp = pool.urlopen(method = method, url = url, body = body, headers = _headers)
    resp = process_response(resp)
    if resp.status in [301, 302]:
        redirect_url = resp.headers.get('location')
        resp = download(url = redirect_url, method = method, params = params, body = body, headers = headers, proxy = proxy)            
    elif resp.status >= 400:
        raise DownloadException(status = resp.status)

    return resp 
    
def process_response(resp):
    status = resp.status
    headers = resp.headers
    data = resp.data
                
    if status == 200:
        charset = None
        mime_type = None
        m = headers.get('content-type') 
                  
        if m:
            fields = m.split(';')
            mime_type = fields[0].lower().strip()
            if len(fields) > 1:
                words = fields[1].split('=')
                if len(words) == 2:
                    if words[0].lower().strip() == 'charset':
                        charset = words[1].strip()
                
        if mime_type == "text/html" and not charset:
            try:
                hxs = HtmlXPathSelector(text = data.lower())
                content_type = hxs.select("//meta[@http-equiv='content-type']/@content").extract()[0]                
                k, v = content_type.split(';')[1].split('=')                    
                if k.lower().strip() == 'charset':
                    charset = v.strip()
            except:
                pass
                
        if charset:
            try:
                data = unicode(data, charset)
            except:
                if charset.lower() == 'gb2312':
                    #try to decode as gbk
                    try:
                        data = unicode(data, 'gbk')
                    except:
                        pass
    
    return Response(status = resp.status, headers = headers, body = data) 