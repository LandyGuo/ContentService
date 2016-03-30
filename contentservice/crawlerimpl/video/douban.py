#coding=utf8
import requests

SOURCE = "douban"

UDID = "f951f2b593f96c3b6c6991169044ae4b1753885a"
CLIENT = "s:mobile|y:Android 4.1.2|o:485486|f:32|v:2.4.1|m:Baidu_Market|d:351554056408231|e:samsung maguro|ss:720x1184"
API_KEY = "0b2bdeda43b5688921839c8ecb20399b"

def api_detail(movie_id):
    url = "http://api.douban.com/v2/movie/subject/%s" % movie_id
    params = {
              "udid" : UDID,
              "client" : CLIENT,
              "apikey" : API_KEY,
              "city" : u"北京",
              }
    resp = requests.get(url, params = params)
    return resp.json()
    
def api_search(query):
    url = "http://api.douban.com/v2/movie/search"
    params = {
              "count" : 1,
              "udid" : UDID,
              "client" : CLIENT,
              "apikey" : API_KEY,
              "q" : query
              }
    resp = requests.get(url, params = params)
    return resp.json()

if __name__ == "__main__":
    title = u"盗梦空间"
    data = api_search(title)
    if data.get('subjects'):
        movie_id = data['subjects'][0]['id']
        info = api_detail(movie_id)
        print info['title'], ",".join(info['genres'])