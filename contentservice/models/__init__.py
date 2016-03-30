#coding=utf8
import sys
from base import ModelBase
import music, ring, novel, video
    
MODEL_TYPES = {}

def find_models(obj, depth = 0):
    if depth > 3:
        return
    if isinstance(obj, type) and issubclass(obj, ModelBase) and obj != ModelBase:
        MODEL_TYPES[obj.TYPE] = obj
    elif type(obj).__name__ == "module":
        for key in dir(obj):
            if not key.startswith("__"):
                find_models(getattr(obj, key), depth + 1)

find_models(sys.modules[__name__])

def create_model(t, dct = {}):
    if dct is None:
        return None
    if t not in MODEL_TYPES:
        raise Exception("Invalid model type - %s" % type)
    return MODEL_TYPES[t](dct)