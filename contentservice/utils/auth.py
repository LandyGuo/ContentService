from hashlib import md5

def calc_signature(params):
    pairs = []
    for key in sorted(params):
        if key == "_signature":
            continue
        value = str(params[key])
        pairs.append(key + "=" + value)
    
    paramString = "&".join(pairs)
    
    salt = "coolpad_"
    sig = md5(salt + paramString).hexdigest()
    return sig