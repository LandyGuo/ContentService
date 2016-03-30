#coding=utf8
import os, re, uuid, hashlib

def ensure_paths(paths):
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)

def ensure_dir(path):
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def filemd5(path):
    with open(path) as fp:
        data = fp.read()
        return hashlib.md5(data).hexdigest()

def get_tmppath(ext = ""):
    while True:
        tmppath = os.path.join("/tmp/", uuid.uuid4().hex)
        if ext:
            tmppath = tmppath + "." + ext
        if not os.path.exists(tmppath):
            return tmppath 

def exists_ignore_case(path):
    dirname = os.path.dirname(path)
    basename = os.path.basename(path)
    for name in os.listdir(dirname):
        if name.lower() == basename.lower():
            return True
    return False

def find_files(path, pattern, ignore_case = False):
    items = []
    for name in os.listdir(path):
        subpath = os.path.join(path, name)
        if os.path.isdir(subpath):
            subitems = find_files(subpath, pattern, ignore_case)
            items.extend(subitems)
        elif os.path.isfile(subpath):
            if ignore_case:                  
                if re.match(pattern.lower(), subpath.lower()):
                    items.append(subpath)
            else:
                if re.match(pattern, subpath):
                    items.append(subpath)
    return items


def find_dirs(path, pattern, ignore_case = False):
    for name in os.listdir(path):
        subpath = os.path.join(path, name)
        if os.path.isdir(subpath):
            if ignore_case:                  
                if re.match(pattern.lower(), subpath.lower()):
                    yield subpath
            else:
                if re.match(pattern, subpath):
                    yield subpath
                    
            for item in find_dirs(subpath, pattern, ignore_case):
                yield item