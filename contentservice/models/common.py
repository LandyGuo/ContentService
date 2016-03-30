#coding=utf8
import codecs

def load_map(path):
    dct = {}
    with codecs.open(path, encoding='utf8') as fp:
        for line in fp.readlines():
            line = line.strip()
            if not line:
                continue
            k,v = line.split()
            dct[k] = v
    return dct