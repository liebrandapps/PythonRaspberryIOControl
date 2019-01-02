import base64
import hashlib
import subprocess
import tempfile
from os.path import basename
from zipfile import ZipFile

import time
import urlparse
import uuid

import datetime
import json
import RPi.GPIO as GPIO
import requests
import os
import uuid

from requests import ConnectionError

from myio.liebrand.phd.handler import Handler
from myio.liebrand.prc import Poller
from myio.liebrand.prc.Entity import Entity, FS20, UltraSonic, Sensor18B20, Switch, HMS100T, Netio230, HMS100TF, KSH300, \
    FS20Sensor, Camera, RpiCam, BMP180, Awning
from myio.liebrand.prc.FieldNames import FN
from myio.liebrand.prc.config import Config
from myio.liebrand.prc.remote.ChromeCast import ChromeCast


class PRCApiHandler(Handler):

    DEFAULT_LOCALE = "en"
    KEY_DICTIONARY = "dictionary_%s"
    KEY_TEXT = "txt_%d"

    def __init__(self, ctx):
        self.cfg = ctx.getConfig()
        self.log = ctx.getLogger()
        self.ctx = ctx
        ctx.api = self
        self.serverId = self.cfg.general_serverId
        self.cfg.setSection(Config.SECTIONS[Config.GENERAL])


        self.peer = ctx.peer
        self.dcts = [ctx.switch, ctx.fs20, ctx.ultrasonic, ctx.sensor18B20, ctx.netio230, ctx.hms100t,
            ctx.hms100tf, ctx.ksh300, ctx.fs20Sensor, ctx.camera, ctx.rpiCam, ctx.bmp180, ctx.awning,
                     ctx.kerui, ctx.zigbee]
        self.switch = ctx.switch
        self.fs20 = ctx.fs20
        self.us = ctx.ultrasonic
        self.temp = ctx.sensor18B20
        self.netio230 = ctx.netio230
        self.hms100t = ctx.hms100t
        self.hms100tf = ctx.hms100tf
        self.ksh300 = ctx.ksh300
        self.fs20Sensor = ctx.fs20Sensor
        self.camera = ctx.camera
        self.rpiCam = ctx.rpiCam
        self.bmp180 = ctx.bmp180
        self.awning = ctx.awning
        self.kerui = ctx.kerui
        self.zigbee = ctx.zigbee
        self.cfg.setSection(Config.SECTIONS[Config.WEB])
        self.headline = self.cfg.headline

        self.startTime = datetime.datetime.now()
        self.sslCert = self.cfg.general_clientCertFile
        self.timeStamps = []


    def endPoint(self):
        return(["/prcapi", ])

    def doGET(self, path, headers):
        index = path.find('?')
        if index == -1:
            return [404, {}, ""]
        tmp=dict((k, v if len(v) > 1 else v[0])
             for k, v in urlparse.parse_qs(path[index + 1:], keep_blank_values=1).iteritems())
        body = json.dumps(tmp)
        return self.doPOST(path, headers, body)

    def doPOST(self, path, headers, body):
        self.log.debug(body[:256])
        if "Host" not in headers:
            return [400, {}, "Host Header is missing"]
        if "Xprotocol" in headers:
            proto = headers["Xprotocol"]
        else:
            proto = "http"
        host = proto + "://" + headers["host"] + self.endPoint()[0]
        dct = {}
        resultHeaders = {}
        resultCode = 500
        fields = json.loads(body)

        if FN.FLD_TIMESTAMP in fields:
            if fields[FN.FLD_TIMESTAMP] in self.timeStamps:
                resultCode = 200
                resultHeaders['Content-Type'] = "application/json"
                dct[FN.FLD_STATUS] = FN.ok
                dct[FN.FLD_MESSAGE] = "duplicate request"
                return [resultCode, resultHeaders, body]
            else:
                self.timeStamps.append(fields[FN.FLD_TIMESTAMP])
                while len(self.timeStamps)>10:
                    self.timeStamps.pop(0)

        if FN.FLD_CMD in fields:
            if fields[FN.FLD_CMD] == FN.CMD_CONFIG:
                resultCode, dct = self.cmdConfig(fields, dct, host)
            elif fields[FN.FLD_CMD] == FN.CMD_SWITCH:
                resultCode, dct = self.cmdSwitch(fields, dct, host)
            elif fields[FN.FLD_CMD] == FN.CMD_STATUS:
                resultCode, dct = self.cmdStatus(fields,dct, host)
            elif fields[FN.FLD_CMD] == FN.CMD_HISTORY24:
                resultCode, dct = self.cmdHistory24(fields, dct, host)
            elif fields[FN.FLD_CMD] == FN.CMD_ABOUT:
                resultCode, dct = self.cmdAbout(fields, dct, host)
            elif fields[FN.FLD_CMD] == FN.CMD_TOKEN:
                resultCode, dct = self.cmdToken(fields, dct, host)
            elif fields[FN.FLD_CMD] == FN.CMD_REFRESH:
                resultCode, dct = self.cmdRefresh(fields, dct)
            elif fields[FN.FLD_CMD] == FN.CMD_SHINE:
                resultCode, dct = self.cmdShine(fields,dct, host)
            elif fields[FN.FLD_CMD] == FN.CMD_CANBACKUP:
                resultCode, dct = self.cmdCanBackup(fields, dct)
            elif fields[FN.FLD_CMD] == FN.CMD_BACKUP:
                resultCode, dct = self.cmdBackup(fields, dct)
            elif fields[FN.FLD_CMD] == FN.CMD_SNAPSHOT:
                resultCode, dct = self.cmdSnapshot(fields, dct, host)
            elif fields[FN.FLD_CMD].startswith('awning'):
                resultCode, dct = self.cmdAwning(fields, dct, host)
            elif fields[FN.FLD_CMD] == FN.CMD_PLAYTLVIDEO:
                resultCode, dct = self.cmdPlayTLVideo(fields, dct, host)
            elif fields[FN.FLD_CMD] == FN.CMD_SHOWSNAPSHOT:
                resultCode, dct = self.cmdShowSnapshot(fields, dct, host)
            elif fields[FN.FLD_CMD] == FN.CMD_RUNSHELLCMD:
                resultCode, dct = self.cmdShellCmd(fields, dct, host)
            else:
                resultCode = 400
                dct[FN.FLD_STATUS] = FN.fail
                dct[FN.FLD_MESSAGE] = "Unsupported command (%s)" % fields[FN.FLD_CMD]
                self.log.error("[PRCAPI] Unsupported Command: %s" % body)
        else:
            resultCode = 400
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing field in JSON (%s)" % FN.FLD_CMD
            self.log.error("[PRCAPI] Error in json cannot match fields: %s" % body)

        body = json.dumps(dct)
        resultHeaders['Content-Type'] = "application/json"
        return [resultCode, resultHeaders, body]

    def cmdConfig(self, fields, dct, host):
        locale = PRCApiHandler.DEFAULT_LOCALE
        if FN.FLD_LOCALE in fields:
            locale = fields[FN.FLD_LOCALE]
        roaming = FN.FLAG_ROAMING in fields
        #
        # Peer Links
        #
        for key in self.peer.keys():
            prdct = {}
            instance = self.peer[key]
            prdct[FN.FLD_NAME] = instance.getName(locale)
            prdct[FN.FLD_ADDRESS] = instance.getAddress()
            dct[instance.entityId] = prdct
        #
        # Actors & Sensors
        #
        for d in self.dcts:
            for key in d.keys():
                data = {}
                instance = d[key]
                data[FN.FLD_NAME] = instance.getName(locale)
                if key.startswith('switch'):
                    value = self.queryCachedActorStatus(key)
                    if value is None:
                        value = instance.wrapper.status(instance.getGPIO())
                    data[FN.FLD_STATUS] = value
                elif key.startswith('fs20') and not(key.startswith('fs20Sensor')):
                    value = self.queryCachedActorStatus(key)
                    if value is None:
                        value = instance.wrapper.status(instance.getAddress())
                    data[FN.FLD_STATUS] = value
                elif key.startswith('ultrasonic'):
                    value = self.queryCachedSensorValue(key)
                    if value is None:
                        value = instance.wrapper.measure()
                    data[FN.FLD_VALUE] = value
                    rg = instance.getRange()
                    data[FN.FLD_MIN] = rg[0]
                    data[FN.FLD_MAX] = rg[1]
                    data[FN.FLD_INVERSE] = instance.getInverse()
                elif key.startswith('temperature'):
                    value = self.queryCachedSensorValue(key)
                    status = "ok"
                    if value is None:
                        status, value = instance.wrapper.measure(instance.getAddress())
                    data[FN.FLD_VALUE] = value
                    data[FN.FLD_STATUS] = status
                    rg = instance.getRange()
                    data[FN.FLD_MIN] = rg[0]
                    data[FN.FLD_MAX] = rg[1]
                elif key.startswith('netio'):
                    data[FN.FLD_STATUS] = instance.status()[1]
                elif key.startswith('hms100t') or key.startswith('ksh300') or key.startswith('fs20Sensor') \
                    or key.startswith('kerui') or key.startswith('zigbee'):
                    data[FN.FLD_VALUE] = self.queryCachedPushSensorValue(key)
                elif key.startswith('camera'):
                    data[FN.FLD_CANSTREAM] = instance.streamingEnabled
                    data[FN.FLD_CANTIMELAPSE] = instance.timelapseEnabled
                    if instance.timelapseEnabled:
                        data[FN.FLD_TIMELAPSEMP4] = basename(instance.timelapseMP4)
                        data[FN.FLD_TIMELAPSECODEC] = instance.timelapseCodec
                elif key.startswith('rpicam'):
                    pass
                elif key.startswith('bmp180'):
                    x = instance.wrapper.measure()
                    data[FN.FLD_VALUE] = "%.1f C | %.2f hPa" % (x[0], x[1])
                elif key.startswith('awning'):
                    pass
                data[FN.FLD_HOST] = host
                data[FN.FLD_LOCALID] = instance.entityId
                data[FN.FLD_SERVERID] = self.serverId
                dct[instance.entityId] = data
        #
        # Roaming
        #
        idxs = [len(self.switch), len(self.fs20), len(self.us), len(self.temp), len(self.netio230),
                len(self.hms100t), len(self.hms100tf), len(self.ksh300), len(self.fs20Sensor), len(self.camera),
                len(self.rpiCam), len(self.bmp180), len(self.awning), len(self.kerui), len(self.zigbee)]
        if roaming:
            for key in self.peer.keys():
                p = self.peer[key]
                if p.getRoamingAddress() is not None:
                    self.log.debug("Roaming: Requesting config from %s" % p.getRoamingAddress())
                    status, resultDct = self.requestPeerConfig(p.getRoamingAddress(), locale)
                    if status == 200 and resultDct is not None:
                        self.stackPeerConfig(dct, resultDct, idxs)
                    else:
                        self.log.warn("Roaming: Peer %s seems to be absent" % p.getRoamingAddress())
        #
        # Update total counts
        #
        counters = [FN.FLD_SWITCHCOUNT, FN.FLD_FS20COUNT, FN.FLD_ULTRASONICCOUNT, FN.FLD_TEMPERATURECOUNT,
                    FN.FLD_NETIOCOUNT, FN.FLD_HMS100TCOUNT, FN.FLD_HMS100TFCOUNT, FN.FLD_KSH300COUNT,
                    FN.FLD_FS20SENSORCOUNT, FN.FLD_CAMERACOUNT, FN.FLD_RPICAMCOUNT, FN.FLD_BMP180COUNT,
                    FN.FLD_AWNING_COUNT, FN.FLD_KERUICOUNT, FN.FLD_ZIGBEECOUNT]
        for c, i in zip(counters, idxs):
            dct[c] = i
        dct[FN.FLD_PEERCOUNT] = len(self.peer)

        dct[FN.FLD_LASTUPDATETIME] = time.time()
        dct[FN.FLD_LASTUPDATETYPE] = "direct query"

        resultCode = 200
        dct[FN.FLD_STATUS] = FN.ok
        return [resultCode, dct]


    def cmdAbout(self, fields, dct, host):
        locale = PRCApiHandler.DEFAULT_LOCALE
        if FN.FLD_LOCALE in fields:
            locale = fields[FN.FLD_LOCALE]
        dct[FN.FLD_NAME] = self.headline
        dct[FN.FLD_PID] = os.getpid()
        timeDelta = datetime.datetime.now() - self.startTime
        seconds = timeDelta.seconds
        days = seconds / 86400
        seconds -= days * 86400
        hours = seconds / 3600
        seconds -= hours * 3600
        minutes = seconds / 60
        seconds -= minutes * 60
        dct[FN.FLD_UPTIME] = [days, hours, minutes, seconds]
        setAddress = []
        for key in self.peer.keys():
            p = self.peer[key]
            if p.getRoamingAddress() is not None:
                self.log.debug("Roaming: Requesting 'about' info from %s" % p.getRoamingAddress())
                status, resultDct = self.requestPeerAbout(p.getRoamingAddress(), locale)
                if status == 200:
                    setAddress.append(p.getRoamingAddress())
                    del resultDct[FN.FLD_DICTIONARY]
                    dct[p.getRoamingAddress()] = resultDct
                else:
                    self.log.warn("Roaming: Peer %s seems to be absent" % p.getRoamingAddress())
        dct[FN.FLD_ADDRESS] = setAddress

        idxs = [len(self.switch), len(self.fs20), len(self.us), len(self.temp), len(self.netio230),
                len(self.hms100t), len(self.hms100tf), len(self.ksh300), len(self.fs20Sensor),
                len(self.camera), len(self.rpiCam), len(self.bmp180), len(self.awning),
                len(self.kerui), len(self.zigbee)]
        counters = [FN.FLD_SWITCHCOUNT, FN.FLD_FS20COUNT, FN.FLD_ULTRASONICCOUNT, FN.FLD_TEMPERATURECOUNT,
                    FN.FLD_NETIOCOUNT, FN.FLD_HMS100TCOUNT, FN.FLD_HMS100TFCOUNT, FN.FLD_KSH300COUNT,
                    FN.FLD_FS20SENSORCOUNT, FN.FLD_CAMERACOUNT, FN.FLD_RPICAMCOUNT, FN.FLD_BMP180COUNT,
                    FN.FLD_AWNING_COUNT, FN.FLD_KERUICOUNT, FN.FLD_ZIGBEECOUNT]
        for c, i in zip(counters, idxs):
            dct[c] = i
        dct[FN.FLD_PEERCOUNT] = len(self.peer)

        section = PRCApiHandler.KEY_DICTIONARY % locale
        lang = {}
        self.cfg.setSection(section)
        for i in range(150):
            key = PRCApiHandler.KEY_TEXT % (i + 1)
            if self.cfg.hasOption(key):
                lang[key] = self.cfg.readValue(key)
            else:
                break
        dct[FN.FLD_DICTIONARY] = lang
        dct[FN.FLD_PUSHENABLED] = self.ctx.fcm.isFCMEnabled
        if self.ctx.fcm.isFCMEnabled:
            dct[FN.FLD_PUBLIC_KEY] = self.ctx.fcm.publicKey
            dct[FN.FLD_SENDER_ID] = self.ctx.fcm.senderId
            dct[FN.FLD_FCMURL] = self.ctx.fcm.url
        resultCode = 200
        return [resultCode, dct]

    def cmdRefresh(self, fields, dct):
        roaming = FN.FLAG_ROAMING in fields

        for d in self.dcts:
            for key in d.keys():
                data = {}
                instance = d[key]
                if key.startswith('switch'):
                    value = instance.wrapper.status(instance.getGPIO())
                    data[FN.FLD_STATUS] = value
                elif key.startswith('fs20') and not(key.startswith('fs20Sensor')):
                    value = instance.wrapper.status(instance.getAddress())
                    data[FN.FLD_STATUS] = value
                elif key.startswith('netio'):
                    value = instance.status()[1]
                    data[FN.FLD_STATUS] = value
                elif key.startswith('ultrasonic'):
                    value = instance.wrapper.measure()
                    data[FN.FLD_VALUE] = value
                elif key.startswith('temperature'):
                    status, value = instance.wrapper.measure(instance.getAddress())
                    data[FN.FLD_VALUE] = value
                    data[FN.FLD_STATUS] = status
                elif key.startswith('hms100') or key.startswith('ksh300') or key.startswith('fs20Sensor') \
                        or key.startswith('kerui') or key.startswith('zigbee'):
                    data[FN.FLD_VALUE] = self.queryCachedPushSensorValue(key)
                elif key.startswith('bmp180'):
                    x = instance.wrapper.measure()
                    data[FN.FLD_VALUE] = "%.1f C | %.2f hPa" % (x[0], x[1])
                dct[instance.entityId] = data

        #
        # Roaming
        #
        idxs = [len(self.switch), len(self.fs20), len(self.us), len(self.temp), len(self.netio230),
                len(self.hms100t), len(self.hms100tf), len(self.fs20Sensor), len(self.camera),
                len(self.rpiCam), len(self.bmp180), len(self.awning), len(self.kerui), len(self.zigbee)]
        if roaming:
            for key in self.peer.keys():
                p = self.peer[key]
                if p.getRoamingAddress() is not None:
                    self.log.debug("Roaming: Requesting refresh for %s" % p.getRoamingAddress())
                    status, resultDct = self.requestPeerRefresh(p.getRoamingAddress())
                    if status == 200 and resultDct is not None:
                        self.stackPeerConfig(dct, resultDct, idxs)
                    else:
                        self.log.warn("Roaming: Peer %s seems to be absent" % p.getRoamingAddress())
        #
        # Update total counts
        #
        counters = [FN.FLD_SWITCHCOUNT, FN.FLD_FS20COUNT, FN.FLD_ULTRASONICCOUNT, FN.FLD_TEMPERATURECOUNT,
                    FN.FLD_NETIOCOUNT, FN.FLD_HMS100TCOUNT, FN.FLD_HMS100TFCOUNT, FN.FLD_KSH300COUNT,
                    FN.FLD_FS20SENSORCOUNT, FN.FLD_CAMERACOUNT, FN.FLD_RPICAMCOUNT, FN.FLD_BMP180COUNT,
                    FN.FLD_AWNING_COUNT, FN.FLD_KERUICOUNT, FN.FLD_ZIGBEECOUNT]
        for c, i in zip(counters, idxs):
            dct[c] = i
        dct[FN.FLD_LASTUPDATETIME] = time.time()
        dct[FN.FLD_LASTUPDATETYPE] = "direct query"

        resultCode = 200
        dct[FN.FLD_STATUS] = FN.ok
        return [resultCode, dct]


    def cmdStatus(self, fields, dct, host):
        if FN.FLD_ID in fields and FN.FLD_HOST in fields:
            key = fields[FN.FLD_ID]
            targetHost = fields[FN.FLD_HOST]
            if host == targetHost:
                swdct = {}
                if key.startswith("switch"):
                    swdct[FN.FLD_STATUS] = self.switch[key].wrapper.status(self.switch[key].getGPIO())
                elif key.startswith("fs20"):
                    swdct[FN.FLD_STATUS] = self.fs20[key].wrapper.status(self.fs20[key].getAddress())
                elif key.startswith("zigbee"):
                    conn = self.ctx.openDatabase()
                    cursor = conn.cursor()
                    swdct[FN.FLD_STATUS] = self.queryCachedPushSensorValue(cursor, key)
                    cursor.close()
                    self.ctx.closeDatabase(conn)
                else:
                    swdct[FN.FLD_STATUS] = self.netio230[key].status()[1]
                dct[FN.FLD_STATUS] = FN.ok
                dct[key] = swdct
            else:
                r = requests.post(targetHost, json=fields, verify=self.sslCert)
                if r.status_code == 200:
                    dct = json.loads(r.text)
            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing fields in JSON (%s &| %s)" % (FN.FLD_ID,
                                                                         FN.FLD_HOST)
        return [resultCode, dct]


    def cmdSwitch(self, fields, dct, host):
        if FN.FLD_ID in fields and FN.FLD_VALUE and FN.FLD_HOST in fields:
            targetHost = fields[FN.FLD_HOST]
            if host == targetHost:
                # we are local
                if FN.FLD_DISABLENOTIFY in fields:
                    disableNotify = fields[FN.FLD_DISABLENOTIFY]
                else:
                    disableNotify = False
                switchId = fields[FN.FLD_ID]
                toSwitchList = switchId.split(':')
                for sw in toSwitchList:
                    if sw.startswith("switch"):
                        gpio = self.switch[sw].getGPIO()
                        result = self.switch[sw].wrapper.switch(gpio, fields[FN.FLD_VALUE])
                    elif sw.startswith("fs20"):
                        address = self.fs20[sw].getAddress()
                        result = self.fs20[sw].wrapper.switch(address, fields[FN.FLD_VALUE])
                    elif sw.startswith("zigbee"):
                        self.zigbee[sw].switch(fields[FN.FLD_VALUE])
                        result = [200, FN.ok]
                    else:
                        result = self.netio230[sw].switch(fields[FN.FLD_VALUE])
                    if FN.FLD_USER in fields:
                        user = fields[FN.FLD_USER]
                    else:
                        user = "unknown"
                    dct[FN.FLD_STATUS] = result[1]
                    if result[1] == FN.fail:
                        dct[FN.FLD_MESSAGE] = "Problem switching."
                    else:
                        now = datetime.datetime.now()
                        sql = "insert into actor(actorId, newValue, user, atTime, status) values (?, ?, ?, ?, ?)"
                        c = self.dbAccess()
                        values = [sw, fields[FN.FLD_VALUE], user, now, result[1]]
                        c[0].execute(sql, values)
                        c[0].commit()
                        self.dbAccess(c)
                        if not disableNotify:
                            messageDict={}
                            messageDict[sw] = {FN.FLD_VALUE: fields[FN.FLD_VALUE],
                                               FN.FLD_TIMESTAMP: str(int(time.time() * 1000)),
                                               FN.FLD_CMD: FN.CMD_SWITCH}
                            messageDict[FN.FLD_SERVERID] = self.serverId
                            messageDict[FN.FLD_MSGTYPE] = "evtUpdate"

                            pn = self.ctx.getPushNotify()
                            payload = pn.buildDataMessage(Poller.Poller.TOPIC_UPDATE, messageDict)
                            pn.pushMessage(payload)
            else:
                # remote switch
                r = requests.post(targetHost, json=fields, verify=self.sslCert)
                if r.status_code == 200:
                    dct = json.loads(r.text)
            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing field in JSON (%s &| %s &| %s)" % (FN.FLD_ID,
                                                                              FN.FLD_VALUE,
                                                                              FN.FLD_HOST)
        return [resultCode, dct]

    #
    # shine is currently only supported for FS20
    #
    def cmdShine(self, fields, dct, host):
        if FN.FLD_ID in fields and FN.FLD_HOST in fields:
            targetHost = fields[FN.FLD_HOST]
            if host == targetHost:
                # we are local
                if FN.FLD_DISABLENOTIFY in fields:
                    disableNotify = fields[FN.FLD_DISABLENOTIFY]
                else:
                    disableNotify = False
                switchId = fields[FN.FLD_ID]
                if switchId.startswith("fs20"):
                    address = self.fs20[switchId].getAddress()
                    useCuno = self.fs20[switchId].getUseCuno()
                    result = self.fs20[switchId].wrapper.shine(address, useCuno)
                    if FN.FLD_USER in fields:
                        user = fields[FN.FLD_USER]
                    else:
                        user = "unknown"
                    dct[FN.FLD_STATUS] = result[1]
                    if result[1] == FN.fail:
                        dct[FN.FLD_MESSAGE] = "Problem switching."
                    else:
                        now = datetime.datetime.now()
                        sql = "insert into actor(actorId, newValue, user, atTime, status) values (?, ?, ?, ?, ?)"
                        values = [switchId, "off", user, now, result[1]]
                        conn = self.ctx.openDatabase()
                        conn.execute(sql, values)
                        conn.commit()
                        self.ctx.closeDatabase(conn)
                        if not disableNotify:
                            messageDict = {}
                            messageDict[switchId] = {FN.FLD_VALUE : "off",
                                                     FN.FLD_TIMESTAMP : str(int(time.time() * 1000)),
                                                     FN.FLD_CMD : FN.CMD_SHINE}
                            messageDict[FN.FLD_SERVERID] = self.serverId
                            messageDict[FN.FLD_MSGTYPE] = "evtUpdate"
                            pn = self.ctx.getPushNotify()
                            payload = pn.buildDataMessage(Poller.Poller.TOPIC_UPDATE, messageDict)
                            pn.pushMessage(payload)
                else:
                    resultCode = 500
                    dct[FN.FLD_STATUS] = FN.fail
                    dct[FN.FLD_MESSAGE] = "Unsupported switch type %s" % (switchId)
            else:
                # remote switch
                r = requests.post(targetHost, json=fields, verify=self.sslCert)
                if r.status_code == 200:
                    dct = json.loads(r.text)
            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing field in JSON (%s &| %s)" % (FN.FLD_ID,
                                                                        FN.FLD_HOST)
        return [resultCode, dct]


    def cmdHistory24(self, fields, dct, host):
        if FN.FLD_ID in fields and FN.FLD_HOST in fields:
            key = fields[FN.FLD_ID]
            targetHost = fields[FN.FLD_HOST]
            if host == targetHost:
                dct[FN.FLD_STATUS] = FN.ok
                if key.startswith('hms100t') or key.startswith('ksh300') or (key.startswith('fs20Sensor')):
                    dct[key] = self.queryPushSensorHistory24(key)
                else:
                    dct[key] = self.querySensorHistory24(key)
            else:
                r = requests.post(targetHost, json=fields, verify=self.sslCert)
                if r.status_code == 200:
                    dct = json.loads(r.text)
            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing fields in JSON (%s &| %s)" % (FN.FLD_ID,
                                                                         FN.FLD_HOST)
        return [resultCode, dct]


    def cmdToken(self, fields, dct, host):
        if FN.FLD_TOKEN in fields and FN.FLD_CLIENTID in fields:
            # token == 0 -> delete token & subscription
            # clientId == 0 -> new client & subscription
            # both != 0 refresh token
            token = fields[FN.FLD_TOKEN]
            clientId = fields[FN.FLD_CLIENTID]
            if len(clientId) == 0:
                clientId = str(uuid.uuid4())
                existingToken = self.getToken(clientId)
                while existingToken is not None:
                    clientId = str(uuid.uuid4())
                    existingToken = self.getToken(clientId)
            if len(token) == 0:
                existingToken = self.getToken(clientId)
                self.log.debug("Going to delete Token %s for client %s" % (existingToken, clientId))
                self.ctx.getPushNotify().unsubscribeFromTopic(existingToken, Poller.Poller.TOPIC_UPDATE)
                self.deleteToken(clientId, existingToken)
            else:
                self.log.debug("Going to save Token %s for client %s" % (token, clientId))
                self.saveToken(clientId, token)
                self.ctx.getPushNotify().subscribeToTopic(token, Poller.Poller.TOPIC_UPDATE)
            dct[FN.FLD_STATUS] = FN.ok
            dct[FN.FLD_CLIENTID] = clientId
            # for key in self.peer.keys():
            #    p = self.peer[key]
            #    if p.getRoamingAddress() is not None:
            #        self.log.debug("Roaming: Updating Subscriptions at %s" % p.getRoamingAddress())
            #        self.updatePeerSubscription(p.getRoamingAddress(), clientId, token)

            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing fields in JSON (%s &| %s)" % (FN.FLD_TOKEN,
                                                                         FN.FLD_CLIENTID)
        return [resultCode, dct]


    def cmdCanBackup(self, fields, dct):
        if FN.FLD_SERVERID in fields:
            if not (self.cfg.hasKey(self.cfg.scope, 'peerBackup')):
                dct[FN.FLD_STATUS] = FN.fail
            else:
                backupCfg = self.cfg.general.peerBackup
                peerBackupPath = os.path.join(backupCfg[0], backupCfg[1], fields[FN.FLD_SERVERID])
                backupMD5 = {}
                if os.path.exists(peerBackupPath):
                    for root, dirs, files in os.walk(peerBackupPath, topdown=True):
                        for name in files:
                            fileName = (os.path.join(root, name))
                            md5 = hashlib.md5()
                            with open(str(fileName), 'rb') as file:
                                buf = file.read()
                                md5.update(buf)
                            backupMD5[name] = md5.hexdigest()
                dct[FN.FLD_BACKUP] = backupMD5
                dct[FN.FLD_STATUS] = FN.ok
            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing field in JSON (%s)" % (FN.FLD_SERVERID)
        return [resultCode, dct]


    def cmdBackup(self, fields, dct):
        if FN.FLD_SERVERID in fields and FN.FLD_NAME in fields and FN.FLD_DATA in fields:
            backupCfg = self.cfg.general.peerBackup
            peerBackupPath = os.path.join(backupCfg[0], backupCfg[1], fields[FN.FLD_SERVERID])
            b64Decoded = base64.b64decode(fields[FN.FLD_DATA])
            tmpFile = tempfile.mktemp()
            with open(tmpFile, "wb") as f:
                f.write(b64Decoded)
            with ZipFile(tmpFile, 'r') as zip:
                for zip_info in zip.infolist():
                    if zip_info.filename[-1] == '/':
                        continue
                    zip_info.filename = os.path.basename(zip_info.filename)
                    zip.extract(zip_info, peerBackupPath)
            os.remove(tmpFile)


            resultCode =200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing field in JSON (%s &| %s &| %s)" % (FN.FLD_SERVERID,
                                                                            FN.FLD_NAME, FN.FLD_DATA)
        return [resultCode, dct]

    def cmdSnapshot(self, fields, dct, host):
        if FN.FLD_ID in fields and FN.FLD_HOST in fields:
            targetHost = fields[FN.FLD_HOST]
            if host == targetHost:
                # we are local
                if fields[FN.FLD_ID].startswith('camera'):
                    ipCam = self.camera[fields[FN.FLD_ID]]
                    result = ipCam.wrapper.getSnapshot(ipCam.snapshotAddress)
                else:
                    ipCam = self.rpiCam[fields[FN.FLD_ID]]
                    result = ipCam.wrapper.getSnapshot()
                if result[0] == 200:
                    dct[FN.FLD_STATUS] = FN.ok
                    dct[FN.FLD_DATA] = base64.b64encode(result[1])
                else:
                    dct[FN.FLD_STATUS] = FN.fail
                    dct[FN.FLD_MESSAGE] ="Cam Snapshot failed with code %d" % result[0]
            else:
                # remote camera
                r = requests.post(targetHost, json=fields, verify=self.sslCert)
                if r.status_code == 200:
                    dct = json.loads(r.text)
            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing field in JSON (%s &| %s)" % (FN.FLD_ID,
                                                                              FN.FLD_HOST)
        return [resultCode, dct]

    def cmdAwning(self, fields, dct, host):
        if FN.FLD_ID in fields and FN.FLD_HOST in fields:
            targetHost = fields[FN.FLD_HOST]
            if host == targetHost:
                # we are local
                wrapper = self.awning[fields[FN.FLD_ID]].wrapper
                cmd = ""
                if fields[FN.FLD_CMD] == FN.CMD_IN:
                    cmd = wrapper.cmdDriveIn
                elif fields[FN.FLD_CMD] == FN.CMD_OUT:
                    cmd = wrapper.cmdDriveOut
                elif fields[FN.FLD_CMD] == FN.CMD_STOP:
                    cmd = wrapper.cmdStop
                if len(cmd) == 0:
                    resultCode = 500
                    dct[FN.FLD_STATUS] = FN.fail
                    dct[FN.FLD_MESSAGE] = "Command for awning not recognized %s" % fields[FN.FLD_CMD]
                else:
                    snd, rcv = wrapper.send(self.awning[fields[FN.FLD_ID]].address, cmd)
                    dct[FN.FLD_STATUS] = FN.ok
                    dct[FN.FLD_MESSAGE] = "snd %s -> rvc %s" % (snd, rcv)
                    resultCode = 200
            else:
                # remote switch
                r = requests.post(targetHost, json=fields, verify=self.sslCert)
                if r.status_code == 200:
                    dct = json.loads(r.text)
            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing field(s) in JSON (%s &| %s)" % (FN.FLD_ID,
                                                                        FN.FLD_HOST)
        return [resultCode, dct]

    def cmdPlayTLVideo(self, fields, dct, host):
        if FN.FLD_CASTNAME in fields and FN.FLD_ID in fields and FN.FLD_HOST in fields:
            targetHost = fields[FN.FLD_HOST]
            if host == targetHost:
                if fields[FN.FLD_ID].startswith('camera'):
                    instance = self.camera[fields[FN.FLD_ID]]
                else:
                    instance = self.rpiCam[fields[FN.FLD_ID]]
                if instance.timelapseEnabled:
                    friendlyName = None
                    for ce in self.ctx.chromeCast.keys():
                        ceO = self.ctx.chromeCast[ce]
                        if ceO.callName.upper() in fields[FN.FLD_CASTNAME].upper():
                            friendlyName = ceO.friendlyName
                            break
                    if friendlyName is None:
                        resultCode = 500
                        dct[FN.FLD_STATUS] = FN.fail
                        dct[FN.FLD_MESSAGE] = "Could not match cast name %s to any configured device" % fields[FN.FLD_CASTNAME]
                        self.log.error(dct[FN.FLD_MESSAGE])
                    else:
                        mediaUrl = self.ctx.cfg.general_addressNoSSL + '/' + basename(instance.timelapseMP4)

                        cc = ChromeCast()
                        cc.log = self.log
                        cc.mediaUrl = mediaUrl
                        cc.mediaType = ChromeCast.MEDIATYPE_MP4
                        cc.friendlyName = friendlyName
                        cc.start()
                        resultCode = 200
                        dct[FN.FLD_STATUS] = FN.ok
                else:
                    resultCode = 500
                    dct[FN.FLD_STATUS] = FN.fail
                    dct[FN.FLD_MESSAGE] = "Camera not configured for timelapse video"
                    self.log.error(dct[FN.FLD_MESSAGE])
            else:
                # remote camera
                r = requests.post(targetHost, json=fields, verify=self.sslCert)
                if r.status_code == 200:
                    dct = json.loads(r.text)
            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing field(s) in JSON (%s &| %s &| %s)" % (FN.FLD_ID,
                                                                        FN.FLD_HOST, FN.FLD_CASTNAME)
        return [resultCode, dct]

    def cmdShowSnapshot(self, fields, dct, host):
        if FN.FLD_CASTNAME in fields and FN.FLD_ID in fields and FN.FLD_HOST in fields:
            targetHost = fields[FN.FLD_HOST]
            if host == targetHost:
                if fields[FN.FLD_ID].startswith('camera'):
                    instance = self.camera[fields[FN.FLD_ID]]
                    mediaUrl = instance.snapshotAddress
                    mediaType = ChromeCast.MEDIATYPE_JPEG
                friendlyName = None
                for ce in self.ctx.chromeCast.keys():
                    ceO = self.ctx.chromeCast[ce]
                    if ceO.callName.upper() in fields[FN.FLD_CASTNAME].upper():
                        friendlyName = ceO.friendlyName
                        break
                if friendlyName is None:
                    resultCode = 500
                    dct[FN.FLD_STATUS] = FN.fail
                    dct[FN.FLD_MESSAGE] = "Could not match cast name %s to any configured device" % fields[FN.FLD_CASTNAME]
                    self.log.error(dct[FN.FLD_MESSAGE])
                else:
                    cc = ChromeCast()
                    cc.log = self.log
                    cc.mediaUrl = mediaUrl
                    cc.mediaType = mediaType
                    cc.friendlyName = friendlyName
                    cc.timeout = 20
                    cc.start()
                    resultCode = 200
                    dct[FN.FLD_STATUS] = FN.ok
            else:
                # remote camera
                r = requests.post(targetHost, json=fields, verify=self.sslCert)
                if r.status_code == 200:
                    dct = json.loads(r.text)
            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing field(s) in JSON (%s &| %s &| %s)" % (FN.FLD_ID,
                                                                        FN.FLD_HOST, FN.FLD_CASTNAME)
        return [resultCode, dct]

    def cmdShellCmd(self, fields, dct, host):
        if FN.FLD_ID in fields and FN.FLD_HOST in fields:
            targetHost = fields[FN.FLD_HOST]
            if host == targetHost:
                shellCmdId = fields[FN.FLD_ID]
                shellCmd = self.ctx.shellCmds[shellCmdId]
                if shellCmd is None:
                    resultCode = 500
                    dct[FN.FLD_STATUS] = FN.fail
                    dct[FN.FLD_MESSAGE] = "Invalid ShellCmd specified: %s" % shellCmdId
                    self.log.error(dct[FN.FLD_MESSAGE])
                else:
                    params = {}
                    if FN.FLD_VALUE in fields:
                        params['value'] = fields[FN.FLD_VALUE]
                    params['clientCertFile'] = self.cfg.general.clientCertFile
                    params['address'] = self.cfg.general.address
                    params['lastEvent'] = 100
                    for entity in shellCmd[1:]:
                        if entity.startswith('peer_'):
                            if entity in self.ctx.peer:
                                params[entity] = self.ctx.peer[entity].roamingAddress
                        elif entity in self.ctx.switch or entity in self.ctx.fs20 or entity in self.ctx.netio230:
                            fields2 = { 'id' : entity, 'host' : self.cfg.general.address }
                            dct2 = {}
                            self.ctx.api.cmdStatus(fields2, dct2, self.cfg.general.address)
                            params[entity] = dct2[entity]['status']
                        else:
                            self.log.warn("[API] Could not resolve parameter %s for shell command of shell cmd id %s" %
                                        (entity, shellCmdId))
                    fd, path = tempfile.mkstemp()
                    with os.fdopen(fd, 'w') as tmpFile:
                        tmpFile.write(json.dumps(params))
                    try:
                        p = subprocess.Popen([shellCmd[0], path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        time.sleep(3)
                        outStrg, errStrg = p.communicate()
                        if len(outStrg) > 0:
                            self.log.debug("CMD [%s] stdout: %s" % (shellCmd[0], outStrg))
                        if len(errStrg) > 0:
                            self.log.error(("CMD [%s] stderr: %s" % (shellCmd[0], errStrg)))
                    except Exception, e:
                        self.log.error("[API] Error executing shell command %s: Reason %s" % (shellCmd[0], e))
            else:
                # remote shell cmd
                r = requests.post(targetHost, json=fields, verify=self.sslCert)
                if r.status_code == 200:
                    dct = json.loads(r.text)
            resultCode = 200
        else:
            resultCode = 500
            dct[FN.FLD_STATUS] = FN.fail
            dct[FN.FLD_MESSAGE] = "Missing field(s) in JSON (%s &| %s)" % (FN.FLD_ID,
                                                                        FN.FLD_HOST)
        return [resultCode, dct]


    def requestPeerConfig(self, address, locale):
        resultDct = None
        dct = {}
        # we are *not* requesting roaming config to avoid endless loops
        dct[FN.FLD_CMD] = FN.CMD_CONFIG
        dct[FN.FLD_LOCALE] = locale
        r = requests.post(address, json=dct, verify=self.sslCert)
        if r.status_code == 200:
            resultDct = json.loads(r.text)
        return [r.status_code, resultDct]

    def requestPeerRefresh(self, address):
        resultDct = None
        dct = {}
        # we are *not* requesting roaming config to avoid endless loops
        dct[FN.FLD_CMD] = FN.CMD_REFRESH
        r = requests.post(address, json=dct, verify=self.sslCert)
        if r.status_code == 200:
            resultDct = json.loads(r.text)
        return [r.status_code, resultDct]


    def requestPeerAbout(self, address, locale):
        resultDct = None
        dct = {}
        # we are *not* requesting roaming config to avoid endless loops
        dct[FN.FLD_CMD] = FN.CMD_ABOUT
        dct[FN.FLD_LOCALE] = locale
        try:
            r = requests.post(address, json=dct, verify=self.sslCert)
            if r.status_code == 200:
                resultDct = json.loads(r.text)
            return [r.status_code, resultDct]
        except ConnectionError:
            return [500, {}]

    def updatePeerSubscription(self, address, clientId, token):
        resultDct = None
        dct = {}
        dct[FN.FLD_CMD] = FN.CMD_TOKEN
        dct[FN.FLD_CLIENTID] = clientId
        dct[FN.FLD_TOKEN] = token
        r = requests.post(address, json=dct, verify=self.sslCert)
        if r.status_code == 200:
            resultDct = json.loads(r.text)
        return resultDct


    def stackPeerConfig(self, localcfg, peerCfg, idxs):
        sections = [Switch.SECTION, FS20.SECTION, UltraSonic.SECTION, Sensor18B20.SECTION, Netio230.SECTION,
                    HMS100T.SECTION, HMS100TF.SECTION, KSH300.SECTION, FS20Sensor.SECTION, Camera.SECTION,
                    RpiCam.SECTION, BMP180.SECTION, Awning.SECTION]

        for s, idx in zip(sections, range(len(idxs))):
            i = 1
            key = s % i
            while key in peerCfg:
                idxs[idx] += 1
                stackKey = s % idxs[idx]
                localcfg[stackKey] = peerCfg[key]
                i += 1
                key = s % i


    def queryCachedSensorValue(self, sensorId):
        sql = "select value1 from SensorShort where sensorId = ? and atTime = (select max(atTime) from SensorShort where sensorId = ?)"
        c = self.dbAccess()
        colValues = [sensorId, sensorId]
        c[1].execute(sql, colValues)
        row = c[1].fetchone()
        result = None
        if row is not None and len(row)>0 and row[0] is not None:
            result = row[0]
        self.dbAccess(c)
        return result

    def queryCachedPushSensorValue(self, sensorId, returnRaw=False, yesterday=False, hourAgo=False):
        if yesterday:
            sql = "select value1, value2, atTime from PushSensorShort where sensorId = ? and atTime = (select max(atTime) from PushSensorShort where sensorId = ? and atTime<(select datetime('now', '-1 day')))"
        elif hourAgo:
            sql = "select value1, value2, atTime from PushSensorShort where sensorId = ? and atTime = (select max(atTime) from PushSensorShort where sensorId = ? and atTime<(select datetime('now', '-1 hour')))"
        else:
            sql = "select value1, value2, atTime from PushSensorShort where sensorId = ? and atTime = (select max(atTime) from PushSensorShort where sensorId = ?)"
        c = self.dbAccess()
        colValues = [sensorId, sensorId]
        c[1].execute(sql, colValues)
        row = c[1].fetchone()
        result = None
        rawResult = None
        if row is not None and len(row)>0 and row[0] is not None:
            if row[1] is None:
                result = str(row[0]) + " | " + str(row[2])
                rawResult = [row[0], row[2]]
            else:
                result = str(row[0]) + " | " + str(row[1]) + "|" + str(row[2])
                rawResult = [row[0], row[1], row[2]]
        self.dbAccess(c)
        return rawResult if returnRaw else result


    def queryCachedActorStatus(self, actorId):
        sql = "select newValue from Actor where actorId = ? and atTime = (select max(atTime) from Actor where actorId = ?)"
        c = self.dbAccess()
        colValues = [actorId, actorId]
        c[1].execute(sql, colValues)
        row = c[1].fetchone()
        result = None
        if row is not None and len(row) > 0 and row[0] is not None:
            result = row[0]
        self.dbAccess(c)
        return result

    def querySensorHistory24(self, sensorId):
        sql = "select hour, quarter, value1, value2 from SensorShort where sensorId = ? order by atTime"
        c = self.dbAccess()
        colValues = [sensorId, ]
        c[1].execute(sql, colValues)
        rows = c[1].fetchall()
        set = []
        for r in rows:
            hour = r[0]
            quarter = r[1]
            ts = "%02d:%02d" % (hour, quarter * 15)
            if r[3] is None:
                set.append([ts, r[2]])
            else:
                set.append([ts, r[2], r[3]])
        if len(set)> 15:
            for s in set:
                if s[0].endswith('5'):
                    s[0] = ""
        if len(set)> 30:
            for s in set:
                if s[0].endswith('30'):
                    s[0] = ""
        self.dbAccess(c)
        return set


    def queryPushSensorHistory24(self, sensorId):
        now = datetime.datetime.now()
        sql = "select value1, value2, atTime from PushSensorShort where sensorId = ? and datetime(attime)>datetime('now', '-24 hours', 'localtime') order by atTime"
        c = self.dbAccess()
        colValues = [sensorId, ]
        c[1].execute(sql, colValues)
        rows = c[1].fetchall()
        set = []
        for r in rows:
            t = round((now - r[2]).seconds / 3600, 2) * (-1)
            if r[1] is None:
                set.append([t, r[0]])
            else:
                set.append([t, r[0], r[1]])
        self.dbAccess(c)
        return set


    def saveToken(self, clientId, newToken):
        self.deleteToken(cursor, clientId, newToken)
        sql = "insert into Subscriptions (clientId, token) values (?, ?)"
        c = self.dbAccess()
        colValues = [clientId, newToken]
        c[1].execute(sql, colValues)
        self.dbAccess(c)

    def getToken(self, clientId):
        sql = "select token from Subscriptions where clientId = ?"
        c = self.dbAccess()
        colValues = [clientId, ]
        c[1].execute(sql, colValues)
        row = c[1].fetchone()
        result = None
        if row is not None and len(row) > 0 and row[0] is not None:
            result = row[0]
        self.dbAccess(c)
        return result

    def deleteToken(self, clientId, token):
        sql = "delete from Subscriptions where clientId = ? and token = ?"
        c = self.dbAccess()
        colValues = [clientId, token]
        c[1].execute(sql, colValues)
        self.dbAccess(c)


    def dbAccess(self, conn=None):
        if conn is None:
            self.ctx.dblock.acquire()
            conn = self.ctx.openDatabase()
            cursor = conn.cursor()
            return [conn, cursor]
        else:
            conn[1].close()
            self.ctx.closeDatabase(conn[0])
            self.ctx.dblock.release()