# -*- coding: utf-8 -*-
import re
import urlparse
import HTMLParser

_HTML_PARSER = HTMLParser.HTMLParser()

'''
text - '3:20'
return  200 sec
'''


def parse_duration(text):
    strs = text.split(':')
    duration = 0
    if len(strs) == 1:
        duration = int(strs[0])
    elif len(strs) == 2:
        duration = int(strs[0]) * 60 + int(strs[1])
    elif len(strs) == 3:
        duration = int(strs[0]) * 3600 + int(strs[1]) * 60 + int(strs[2])

    return duration

'''
text - '100k'
return 1024000
'''


def parse_size(text):
    text = text.strip().lower()
    m = re.match('^([\d\.]+)([kmgt]?)', text)
    size = float(m.group(1))
    unit = m.group(2)
    if unit == 'k':
        size *= 1024
    elif unit == 'm':
        size *= 1024 * 1024
    elif unit == 'g':
        size *= 1024 * 1024 * 1024
    elif unit == 't':
        size *= 1024 * 1024 * 1024 * 1024

    return int(size)

    '''        
    真感觉(EPSON最新广告歌曲)
    谁愿放手光年(Trance Mix) [Duet WAndy Hui]
    卡通Medley：传说、飘零燕、IQ博士
    南海姑娘+Talking
    Talking + 如果有一天
    一点点力量+有时候没时候+爱上了(Remix版)
    爱,很简单(Original 1993 English Demo)+心乱飞
    十蚊三个...(原曲_零4好玩_)
    夜半轻私语vs张学友
    Shake Shake 摇滚
    Medley 每当变幻时 明日话今天 仙花满月楼
    死神再呼唤 - The Ghoul Cries Again
    '''


def extract_key(text):
    if not text:
        return ""
    if not isinstance(text, unicode):
        text = unicode(text, 'utf8')

#     text = re.sub(r'\(.*\)', ' ', text)
#     text = re.sub(r'\[.*\]', ' ', text)
#     text = re.sub(u"（.*）", ' ', text)

    chinese_symbols = u"[“”‘’！？—…。，·：、￥（）【】《》〖〗]"
    en_symbols = r'[`~!@#\$%\^&\*\(\)_\+=\-\{\}\[\];:\",\.<>/\?\\|' + "\']"
    text = re.sub(chinese_symbols, ' ', text)
    text = re.sub(en_symbols, ' ', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip().lower()


'''
Whether is likely a valid content text.
Only contains normal characters
'''


def is_valid_content(text, maxlength=-1):
    if not isinstance(text, basestring):
        return False
    if maxlength > 0 and len(text) > maxlength:
        return False
    # TBD not implemented
    return True


def clean_list(lst):
    s = set([clean_text(item) for item in lst])
    ret = []
    for key in s:
        if key not in ["", None]:
            ret.append(key)
    return ret


def clean_url(url):
    url = clean_text(url)

    p = urlparse.urlparse(url)
    if not (p.scheme and p.netloc and p.path):
        return ""
    return p.geturl()


def clean_text(text):
    try:
        text = _HTML_PARSER.unescape(text).strip()
    except:
        return u""
    return text


def clean_title(title):
    title = "".join(title.split())
    return title


def clean_paragraph(text):  # TODO: <br/>
    lines = []
    for line in clean_text(text).split("\n"):
        line = line.strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def is_uuid(text):
    m = re.match("^[0-9a-f]{32}$", text)
    return True if m else False


def split(text):
    if not text:
        return []
    separators = u",;|#&"
    for s in separators:
        text = text.replace(s, " ")
    text = re.sub("\s+", " ", text)
    splits = text.strip().split(" ")
    if len(splits) == 1 and not splits[0]:
        return []
    else:
        return splits

if __name__ == "__main__":
    s = extract_key("123哈哈（）")
    print s
