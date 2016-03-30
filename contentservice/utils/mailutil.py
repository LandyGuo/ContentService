'''
Created on Dec 28, 2012

@author: Yu
'''

import os
import mimetypes
from subprocess import Popen, PIPE

from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

COMMASPACE = ', '

def sendmail(subject, recipients, sender, content = "", attachments = []):
   
    outer = MIMEMultipart()
    outer['Subject'] = subject
    outer['To'] = COMMASPACE.join(recipients) if isinstance(recipients, list) else recipients
    outer['From'] = sender
    outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'


    outer.attach(MIMEText(content))

    for path in attachments:
        # Guess the content type based on the file's extension.  Encoding
        # will be ignored, although we should check for simple things like
        # gzip'd or compressed files.
        ctype, encoding = mimetypes.guess_type(path)
        if ctype is None or encoding is not None:
            # No guess could be made, or the file is encoded (compressed), so
            # use a generic bag-of-bits type.
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        if maintype == 'text':
            fp = open(path)
            # Note: we should handle calculating the charset
            msg = MIMEText(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'image':
            fp = open(path, 'rb')
            msg = MIMEImage(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'audio':
            fp = open(path, 'rb')
            msg = MIMEAudio(fp.read(), _subtype=subtype)
            fp.close()
        else:
            fp = open(path, 'rb')
            msg = MIMEBase(maintype, subtype)
            msg.set_payload(fp.read())
            fp.close()
            # Encode the payload using Base64
            encoders.encode_base64(msg)
        # Set the filename parameter
        filename = os.path.basename(path)
        msg.add_header('Content-Disposition', 'attachment', filename=filename)
        outer.attach(msg)
    # Now send or store the message
    composed = outer.as_string()

    p = Popen(["sendmail", "-t"], stdin=PIPE)
    p.communicate(composed)

    # s = smtplib.SMTP('localhost')
    # s.sendmail(sender, recipients, composed)
    # s.quit()

if __name__ == "__main__":
    sendmail("subject", "yxia@bainainfo.com", "sender", "content")
