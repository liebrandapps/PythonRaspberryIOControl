import json
import os
import sys
import time
from datetime import datetime

import requests

if __name__ == '__main__':
    paramFile = sys.argv[1]
    with open(paramFile) as f:
        params = json.load(f)
    os.remove(paramFile)
    now = datetime.now()
    sslCert = params['clientCertFile']
    lastEvent = params['lastEvent']
    address = params['address']
    if lastEvent == 0 or lastEvent > 120:
        if now.hour > 17 or now.hour < 8:
            if params['fs20_2'] == 'on':
                switches = 'switch_10'
            else:
                switches = 'fs20_2:switch_10'
            dct = {}
            dct['command'] = 'switch'
            dct['value'] = 'on'
            dct['id'] = switches
            dct['user'] = __file__
            dct['host'] = address
            dct['disableNotify'] = True
            r = requests.post(address, json=dct, verify=sslCert)
            if r.status_code == 200:
                resultDct = json.loads(r.text)
                print resultDct
                time.sleep(120)
                dct['value'] = 'off'
                r = requests.post(address, json=dct, verify=sslCert)
                if r.status_code == 200:
                    resultDct = json.loads(r.text)
                else:
                    print r.status_code
            else:
                print r.status_code