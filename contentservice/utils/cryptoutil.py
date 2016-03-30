import os
import M2Crypto

_PUB_KEY_FILE = os.path.join(os.path.dirname(__file__), "../rsa.pub")
_PRIV_KEY_FILE = os.path.join(os.path.dirname(__file__), "../rsa")
_BLOCK_SIZE = 128
_PADDING = M2Crypto.RSA.no_padding

def private_encrypt(data):
    return encrypt(data, public = False)

def public_encrypt(data):
    return encrypt(data)

def private_decrypt(data):
    return decrypt(data)

def public_decrypt(data):
    return decrypt(data, private = False)

def decrypt(data, private = True):
    rsa = M2Crypto.RSA.load_key(_PRIV_KEY_FILE)
    block_size = _BLOCK_SIZE
    try:
        blocks_decrypt = []
        for start in range(0, len(data), block_size):
            block = data[start : start + block_size]
            if private:
                block_decrypt = rsa.private_decrypt(block, _PADDING)
            else:
                block_decrypt = rsa.public_decrypt(block, _PADDING)
                
            size = ord(block_decrypt[_BLOCK_SIZE - 1])
            block_decrypt = block_decrypt[:size]
            blocks_decrypt.append(block_decrypt)
        
        if blocks_decrypt:
            blocks_decrypt[-1] = blocks_decrypt[-1].rstrip("\x00")
        data_decrypt = "".join(blocks_decrypt)
    except Exception, e:
        return None
    
    return data_decrypt

def encrypt(data, public = True):
    rsa = M2Crypto.RSA.load_key(_PRIV_KEY_FILE)
    block_size = _BLOCK_SIZE
    blocks_encrypt = []
    for start in range(0, len(data), block_size - 1):
        block = data[start : start + block_size - 1]
        size = len(block)
        if size < _BLOCK_SIZE - 1:
            block += "\x00" * (_BLOCK_SIZE - 1 - size)
        block += chr(size)
        
        if public:
            block_encrypt = rsa.public_encrypt(block, _PADDING)
        else:
            block_encrypt = rsa.private_encrypt(block, _PADDING)
        blocks_encrypt.append(block_encrypt)

    data_encrypt = "".join(blocks_encrypt)

    return data_encrypt

def gen_key():
    M2Crypto.Rand.rand_seed(os.urandom(1024))
    newkey = M2Crypto.RSA.gen_key(1024, 65537)
    newkey.save_key('/tmp/private.pem', None)
    newkey.save_pub_key('/tmp/public.pem')