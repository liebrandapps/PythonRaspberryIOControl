import json
import select
import threading
import time
from datetime import datetime

from websocket import create_connection


class SonoffWrapper:


    def __init__(self):
        self.status = {}
        self.ws = None
        self.expect = 0
        self.deviceId = None
        self.apikey = None
        self.lastUpdate = None


    def _initMsg(self):
        return json.dumps({
            'action': "userOnline",
            'ts' : int(time.time()),
            'version' : 7,
            'apikey': 'nonce',
            'sequence': str(time.time()).replace('.',''),
            'userAgent': 'app'
        })

    def _updateMessage(self, state, outlet=None):
        dct = {
            'action' : 'update',
            'deviceid' : self.deviceId,
            'apikey': self.apikey,
            'selfApikey': 'nonce',
            'sequence': str(time.time()).replace('.',''),
            'userAgent': 'app'
        }
        if outlet is None:
            dct['params']= { 'switch' : state }
        else:
            s = []
            for o in outlet:
                s.append({ 'switch' : state, 'outlet': o })
            dct['params'] =  {'switches': s}
        return json.dumps(dct)

    def receiver(self):
        try:
            loops = 0
            while loops < self.expect:
                sock = [self.ws.sock,]
                ready = select.select(sock, [],[], 1)
                if len(ready[0])>0 and ready[0][0]==self.ws.sock:
                    result = self.ws.recv()
                    #print("Received '%s'" % result)
                    dct = json.loads(result)
                    if 'deviceid' in dct and dct['deviceid']!='nonce':
                        self.deviceId = dct['deviceid']
                    if 'apikey' in dct and dct['apikey']!='nonce':
                        self.apikey = dct['apikey']
                    if 'action' in dct and dct['action']=='update':
                        tmp = dct['params']['switches']
                        self.status = {}
                        for o in tmp:
                            self.status[o['outlet']] = o['switch']
                        self.lastUpdate = datetime.now()
                loops += 1
        except:
            pass

    def initMsg(self, address):
        now = datetime.now()
        if self.lastUpdate == None or ((now - self.lastUpdate).seconds > 5 and (now - self.lastUpdate).days == 0):
            self.ws = create_connection("ws://%s:8081" % address)
            self.expect = 2
            t = threading.Thread(target=self.receiver)
            t.daemon = True
            t.start()
            dta = self._initMsg()
            self.ws.send(dta)
            t.join()
            self.ws.close()


    def updateMsg(self, address, state, outlet=None):
        ws = create_connection("ws://%s:8081" % address)
        self.expect = 1
        t = threading.Thread(target=self.receiver)
        t.daemon = True
        t.start()
        dta = self._updateMessage(state, outlet)
        ws.send(dta)
        t.join()
        ws.close()
