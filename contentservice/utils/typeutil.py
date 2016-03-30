from datetime import datetime

def dct_to_obj(obj, dct):
    changed = False
    for k, v in dct.iteritems():
        if hasattr(obj, k) and v:
            if getattr(obj, k) != v:
                setattr(obj, k, v)
                changed = True
    return changed   

def merge_dct(dct1, dct2):
    dct = dct1.copy()
    for k, v in dct2.iteritems():
        dct[k] = v
    return dct

def convert(value, t):
    try:
        if t == unicode:
            if isinstance(value, str):
                return unicode(value, 'utf8')
            else:
                return unicode(value)
        elif t == str:
            if isinstance(value, unicode):
                return value.encode('utf8')
            else:
                return str(value)
        elif t == int:
            return int(value) if value else 0
        elif t == long:
            return long(value) if value else 0
        elif t == float:
            return float(value) if value else 0.0
        elif t == datetime:
            if isinstance(value, int) or isinstance(value, long) or isinstance(value, float):
                return datetime.utcfromtimestamp(value)
    except:
        return None
    
    return None

def verify_structure(data, template):
    '''
    Verify the data structure matches the template
    Please refer to _TEST_DATA below
    '''
    if not match_type(data, template):
        raise Exception("Type is not match - (%s, %s)" % (data, template))
    
    if isinstance(data, list) and template:
        for item in data:
            verify_structure(item, template[0])
    elif isinstance(data, dict) and template:
        for key, value in template.iteritems():
            if key:
                if not data.has_key(key):
                    raise Exception("key %s not found" % key)
                verify_structure(data[key], value)
            else: #default template for all other keys
                for k, v in data.iteritems(): 
                    if not template.has_key(k): 
                        verify_structure(v, value)
            
    elif isinstance(data, tuple):
        if len(data) != len(template):
            raise Exception("Tuple is not match - (%s, %s)" % (data, template))
        for i in range(len(data)):
            verify_structure(data[i], template[i])
            
def match_type(v1, v2):
    if isinstance(v1, basestring):
        return isinstance(v2, basestring)
    elif isinstance(v1, (int, long, float)):
        return isinstance(v2, (int, long, float))
    else:
        return v1.__class__ == v2.__class__
    

_TEST_DATA = [ #data, template, result
              (None, None, True),
              (1, 2, True),
              (1, 0.5, True),
              (10L, 5.0, True),
              (1, "str", False),
              ("str1", u"str2", True),
              ([1,2], [], True),
              ([1, "str"], [0], False),
              ((1.0, 1L), (1, 2), True),
              ((1), (1, 2, 3), False),
              (("s", "s"), (1.0, 1.0), False),
              ({"k":1}, {}, True),
              ({}, {"k1" : 0}, False),
              ({"k1":5, "k2":"v"}, {"k1":1, "k2":"str"}, True),
              ({"k1":5, "k2":5}, {"k1":0, "k2":"str"}, False),
              ({"k" : "v"}, {"" : 1}, False),
              ({"k" : "v", "k2" : "v"}, {"" : "v"}, True),
              ({"k1":[1, 2], "k2" : {"k1" : 0, "k2" : False}, "k3" : 5}, {"k1" : [1], "k2" : {"k1" : 1, "k2" : True}, "k3" : 1}, True),
              ]

if __name__ == "__main__":
    for data, template, result in _TEST_DATA:
        try:
            verify_structure(data, template)
            ret = True
        except:
            ret = False
        if result != ret:
            print data, template, result
            