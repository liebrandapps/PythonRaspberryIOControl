import json
import os
import sys
from datetime import datetime

import requests

if __name__ == '__main__':
    paramFile = sys.argv[1]
    with open(paramFile) as f:
        params = json.load(f)
    #os.remove(paramFile)
    print params
    now = datetime.now()
    sslCert = params['clientCertFile']
    lastEvent = params['lastEvent']
    address = params['address']
    if lastEvent == 0 or lastEvent > 5:
        if params['zigbee_2'] == 'click:right':
            dct = {}
            dct['command'] = 'switch'
            if params['netio_6'] == 'off':
                dct['value'] = 'on'
            else:
                dct['value'] = 'off'
            if 'value' in params:
                dct['value'] = params['value']
            dct['user'] = __file__
            dct['host'] = address
            dct['disableNotify'] = True
            dct['id'] = 'netio_6:netio_7:switch_1:switch_3'
            print "About to Switch " + dct['id']
            r = requests.post(address, json=dct, verify=sslCert)
            if r.status_code == 200:
                resultDct = json.loads(r.text)
                print resultDct
            else:
                print r.status_code
            peerHost = params['peer_2']
            print "About to Switch " + dct['id'] + "@" + peerHost
            dct['id'] = 'switch_1'
            dct['host'] = peerHost
            r = requests.post(address, json=dct, verify=sslCert)
            if r.status_code == 200:
                resultDct = json.loads(r.text)
                print resultDct
            else:
                print r.status_code
        if params['zigbee_2'] == 'click:left':
            dct = {}
            dct['command'] = 'switch'
            if params['netio_2'] == 'off':
                dct['value'] = 'on'
            else:
                dct['value'] = 'off'
            if 'value' in params:
                dct['value'] = params['value']
            dct['user'] = __file__
            dct['host'] = address
            dct['disableNotify'] = True
            dct['id'] = 'netio_2:switch_4:switch_10:fs20_2:fs20_4'
            print "About to Switch " + dct['id']
            r = requests.post(address, json=dct, verify=sslCert)
            if r.status_code == 200:
                resultDct = json.loads(r.text)
                print resultDct
            else:
                print r.status_code
            peerHost = params['peer_2']
            print "About to Switch " + dct['id'] + "@" + peerHost
            dct['id'] = 'switch_4:switch_5'
            dct['host'] = peerHost
            r = requests.post(address, json=dct, verify=sslCert)
            if r.status_code == 200:
                resultDct = json.loads(r.text)
                print resultDct
            else:
                print r.status_code
