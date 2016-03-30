#coding=utf8
import os, gzip
from contentservice.models.novel import NovelSourceModel
from contentservice.settings import STATIC_BASE

def save_txt(source, source_id, index, content):
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)
    content = "\n".join(lines)
    
    path = NovelSourceModel({
                      "source_id" : source_id,
                      "source" : source,
                      }).txt_path(index)
                  
    fullpath = os.path.join(STATIC_BASE, "novel/txt", path)
    if not os.path.exists(os.path.dirname(fullpath)):
        try:
            os.makedirs(os.path.dirname(fullpath))
        except:
            pass
    
    with gzip.open(fullpath, "wb") as fp:
        data = content.encode('utf8')
        fp.write(data)
        
if __name__ == "__main__":
    pass