import base64
import requests
import smtplib

from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

urls = [
    'http://192.168.0.113/onvifsnapshot/media_service/snapshot?channel=1&subtype=0',
    'http://192.168.0.107/cgi-bin/getsnapshot.cgi',
    'http://192.168.0.110/cgi-bin/getsnapshot.cgi',
    'http://192.168.0.108/cgi-bin/getsnapshot.cgi'
]

mailHost='smtp.1und1.de'
mailPort='587'
mailUser='telefon@liebrand.eu'
mailPassword='Kati1974'


def sendMailAttachment(mailFrom, mailTo, subject, body, names, attachments):
    msg = MIMEMultipart()
    msg['From'] = mailFrom + '<' + mailUser + '>'
    msg['To'] = mailTo
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach( MIMEText(body +"\n") )

    idx =0
    for a in attachments:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( a )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % (names[idx ] +".jpg"))
        msg.attach(part)
        idx+=1
    smtpserver = smtplib.SMTP(mailHost, mailPort)
    smtpserver.ehlo()
    smtpserver.starttls()
    smtpserver.login(mailUser, mailPassword)
    smtpserver.sendmail(mailUser, mailTo, msg.as_string())
    smtpserver.close()


def getSnapshot(url):
    r=requests.get(url)
    pic = None
    if r.status_code == 200:
        pic = r.content
    return [r.status_code, pic]


if __name__ == '__main__':
    pics = []
    for url in urls:
        result = getSnapshot(url)
        if result[0] == 200:

            pics.append(result[1])
    sendMailAttachment("PRC", 'm.liebrand@bluewin.ch', "Doorbell", "---", urls, pics)


