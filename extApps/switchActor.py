import json
import sys
from datetime import datetime

import requests

if __name__ == '__main__':
    switches = sys.argv[2]
    value = sys.argv[1]
    now = datetime.now()
    sslCert = '/root/dev/prc/ssl/ca.crt'
    address = 'https://192.168.0.196:8020/prcapi'
    dct = {}
    dct['command'] = 'switch'
    dct['value'] = value
    dct['id'] = switches
    dct['user'] = __file__
    dct['host'] = address
    dct['disableNotify'] = True
    r = requests.post(address, json=dct, verify=sslCert)
    if r.status_code == 200:
        resultDct = json.loads(r.text)
        print resultDct
    else:
        print r.status_code