import base64
import hashlib
import json
import os
import subprocess
import tempfile
from random import randint
from zipfile import ZipFile

import requests
import time

from datetime import datetime
import threading
import humanize

from myio.liebrand.prc.SQLProcessor import SQLProcessor
from myio.liebrand.prc.FieldNames import FN
from myio.liebrand.prc.remote.Camera import IPCamera


class Poller(threading.Thread):

    WAITSECS = 900

    TOPIC_UPDATE = "update"
    KEY_MSGTYPE = "msgType"
    KEY_TIMESTAMP = "timeStamp"

    def __init__(self, ctx):
        threading.Thread.__init__(self)
        self.log = ctx.getLogger()
        self.cfg = ctx.cfg
        self.ctx = ctx
        self.terminate = False
        self.wakeup = threading.Event()
        self.serverId = ctx.getConfig().general_serverId
        self.backup = False
        if self.cfg.hasKey(self.cfg.scope['general'], 'peerBackup'):
            backupCfg = self.cfg.general.peerBackup
            if len(backupCfg)<2:
                self.log.warn("[Poller] Peer Backup not configured properly")
            if len(backupCfg)>2:
                self.backup = True
        self.extAppInProgress = {}


    def run(self):
        self.log.info("Starting Poll Thread")
        nextBackup = randint(1,24)
        now = datetime.now()
        quarter = now.minute / 15
        nextQuarter = (quarter + 1) * 15
        delta = (nextQuarter - now.minute - 1) * 60 + (60 - now.second)
        self.log.debug("[Poller] Waiting for %d seconds until the next quarter starts" % (delta))
        if self.backup:
            self.log.info("[Poller] Next backup scheduled in approx. %d minutes" % (nextBackup * Poller.WAITSECS / 60))
        tmp=self.wakeup.wait(delta)
        #self.log.debug(tmp)
        self.wakeup.clear()
        while not(self.terminate):
            now = datetime.now()
            sqls = []
            hour = now.hour
            quarter = now.minute / 15
            slot = hour * 10 + quarter
            if hour == 0 and quarter == 0:
                slot = 240
            messageDict = {}
            sql = "delete from SensorShort where hour = ? and quarter = ?"
            colValues = [hour, quarter]
            sqls.append([sql, colValues])
            sensor18DS20 = self.ctx.sensor18B20
            for key in sensor18DS20.keys():
                instance = sensor18DS20[key]
                value = instance.measure()
                sql = "insert into SensorShort(sensorId, value1, hour, quarter, slot, atTime) values (?, ?, ?, ?, ?, ?)"
                colValues = [key, value[1], hour, quarter, slot, now]
                sqls.append([sql, colValues])
                messageDict[key] = value[1]
            us = self.ctx.ultrasonic
            for key in us.keys():
                instance = us[key]
                value = instance.measure()
                sql = "insert into SensorShort(sensorId, value1, hour, quarter, slot, atTime) values (?, ?, ?, ?, ?, ?)"
                colValues = [key, value, hour, quarter, slot, now]
                sqls.append([sql, colValues])
                messageDict[key] = value
            bmp = self.ctx.bmp180
            for key in bmp.keys():
                instance = bmp[key]
                value = instance.wrapper.measure()
                sql = "insert into SensorShort(sensorId, value1, value2, hour, quarter, slot, atTime) values (?, ?, ?, ?, ?, ?, ?)"
                colValues = [key, value[0], value[1], hour, quarter, slot, now]
                sqls.append([sql, colValues])
                messageDict[key] = value

            self.ctx.sqlProcessor.addSQL([SQLProcessor.CMD_SQLMULTI, sqls])

            if self.ctx.fcm.isFCMEnabled:
                # topic message regular Update
                messageDict[FN.FLD_SERVERID] = self.serverId
                messageDict[Poller.KEY_MSGTYPE] = "regUpdate"
                messageDict[Poller.KEY_TIMESTAMP] = str(int(time.time()*1000))
                pn = self.ctx.getPushNotify()
                messageDict[FN.FLD_ACCESSTOKEN] = pn.get_access_token()
                payload = pn.buildDataMessage(Poller.TOPIC_UPDATE, messageDict)
                pn.pushMessageDirect(payload)
                # topic message for event updates
                combinedDict = {}
                combinedDict[FN.FLD_SERVERID] = self.serverId
                combinedDict[Poller.KEY_TIMESTAMP] = str(int(time.time() * 1000))
                combinedDict[Poller.KEY_MSGTYPE] = "evtUpdate"
                self.ctx.dblock.acquire()
                conn = self.ctx.openDatabase()
                cursor = conn.cursor()
                sql = "select rowid, payload from PNQueue"
                cursor.execute(sql)
                rows = cursor.fetchall()
                if len(rows)>0:
                    sql = "delete from PNQueue where rowid = ?"
                    rowIds = []
                    for r in rows:
                        dta = json.loads(r[1])
                        sub = dta['message']['data']
                        for k in sub.keys():
                            if k != FN.FLD_SERVERID and k != Poller.KEY_MSGTYPE:
                                if k not in combinedDict or sub[k][FN.FLD_TIMESTAMP]>combinedDict[k][FN.FLD_TIMESTAMP]:
                                    combinedDict[k] = sub[k]
                        rowIds.append(r[0])
                    sql = "delete from PNQueue where rowid in (?)"
                    colValues = [",".join(str(r) for r in rowIds),]
                    cursor.execute(sql, colValues)
                    #for k in combinedDict.keys():
                    #    if k != FN.FLD_SERVERID and k != Poller.KEY_MSGTYPE:
                    #        combinedDict[k] = json.dumps(combinedDict[k])
                    payload = pn.buildDataMessage(Poller.TOPIC_UPDATE, combinedDict)
                    pn.pushMessageDirect(payload)
                conn.commit()
                cursor.close()
                self.ctx.closeDatabase(conn)
                self.ctx.dblock.release()
                if self.ctx.rdb.enabled:
                    accessToken = pn.get_access_token()
                    self.ctx.rdb.updateToken(accessToken, self.ctx.fcm.url, self.ctx.cfg.general_address)

            if self.ctx.rdb.enabled:
                ksh300 = self.ctx.ksh300
                for key in ksh300.keys():
                    instance = ksh300[key]
                    if instance.googleActionVerbs is not None:
                        value = self.ctx.api.queryCachedPushSensorValue(key, returnRaw=True)
                        if instance.googleActionResponses is not None:
                            temperature = value[0]
                            humidity = value[1]
                            # ago will be inaccurate by at max 15 minutes
                            ago = humanize.naturaltime(now - value[2])
                            value24 = self.ctx.api.queryCachedPushSensorValue(key, returnRaw=True, yesterday=True)
                            temperature24 = value[0]
                            humidity24 = value[1]
                            value60 = self.ctx.api.queryCachedPushSensorValue(key, returnRaw=True, hourAgo=True)
                            temperature60 = value[0]
                            humidity60 = value[1]
                            if temperature > temperature24:
                                delta24 = temperature - temperature24
                                delta24Text = self.ctx.rdb.more
                            else:
                                delta24 = temperature24 - temperature
                                delta24Text = self.ctx.rdb.less
                            if temperature > temperature60:
                                delta60 = temperature - temperature60
                                delta60Text = self.ctx.rdb.more
                            else:
                                delta60 = temperature60 - temperature
                                delta60Text = self.ctx.rdb.more
                            responses = instance.googleActionResponses
                            ln = len(responses)-1

                        for sensorName in instance.googleActionVerbs:
                            if instance.googleActionResponses is not None:
                                idx = 0 if ln == 0 else randint(0, ln)
                                response = instance.googleActionResponses[idx].format(**locals())
                            else:
                                response = None
                            self.ctx.rdb.updateSensorTH(sensorName, value, response=response)

                sensor18DS20 = self.ctx.sensor18B20
                for key in sensor18DS20.keys():
                    instance = sensor18DS20[key]
                    if instance.googleActionVerbs is not None:
                        value = instance.measure()
                        for sensorName in instance.googleActionVerbs:
                            self.ctx.rdb.updateSensorT(sensorName, value[1])

                fs20Sensor = self.ctx.fs20Sensor
                for key in fs20Sensor.keys():
                    instance = fs20Sensor[key]
                    if instance.googleActionVerbs is not None:
                        value = self.ctx.api.queryCachedPushSensorValue(key, returnRaw=True)
                        if value is not None:
                            peerUpdateisNewer = False
                            if len(instance.peerSensors)>0:
                                for peerKey in instance.peerSensors:
                                    peerValue = self.ctx.api.queryCachedPushSensorValue(key, returnRaw=True)
                                    if peerValue is not None and peerValue[1] > value[1]:
                                        peerUpdateisNewer = True
                                        break
                            if not peerUpdateisNewer:
                                ago = humanize.naturaltime(now - value[1])
                                for sensorName in instance.googleActionVerbs:
                                    if instance.googleActionResponses is not None and not len(instance.googleActionResponses) == 0:
                                        ln = len(instance.googleActionResponses)-1
                                        idx = 0 if ln == 0 else randint(0, ln)
                                        response = instance.googleActionResponses[idx].format(**locals())
                                    else:
                                        response = None
                                    self.ctx.rdb.updateSensorS(sensorName, instance.entityId, value[0], ago, response)

                        #self.log.debug(key)
                        #self.log.debug(value)
                        #self.log.debug(instance.googleActionResponses)

            #sql = "select token from subscriptions"
            #cursor.execute(sql)
            #rows = cursor.fetchall()
            #payload = pn.buildMessage(Poller.TOPIC_UPDATE, "Update", "abc", json.dumps(messageDict))
            #pn.pushMessage(payload)
            #for r in rows:
            #    continue
            #    to = str(r[0])
            #    payload = pn.buildMessage(to, "Update", "abc", json.dumps(messageDict))
            #    pn.pushMessage(payload)

            # sql processor
            self.ctx.sqlProcessor.addSQL([SQLProcessor.CMD_PUSHSENSORLONG])

            # transfer into long table every 6 hours
            if (hour % 6 == 0) and quarter == 0:
                self.ctx.dblock.acquire()
                conn = self.ctx.openDatabase()
                cursor = conn.cursor()
                day_of_year = datetime.now().timetuple().tm_yday
                if hour == 0:
                    qValMax = 240
                    qValMin = 180
                    q = 4
                    day_of_year -= 1
                    if day_of_year == 0:
                        day_of_year = 365
                else:
                    qValMax = hour * 10
                    qValMin = (hour - 6) * 10
                    q = hour / 6
                if hour == 6:
                    sql = "delete from SensorLong where day=?"
                    colValues = [day_of_year,]
                    cursor.execute(sql, colValues)
                sql = "select distinct sensorId from SensorShort"
                cursor.execute(sql)
                rows = cursor.fetchall()
                for r in rows:
                    key = r[0]
                    sql = "select avg(value1), min(value1), max(value1) from SensorShort where slot > ? and slot <= ? and sensorId = ?"
                    colValues = [qValMin, qValMax, key]
                    cursor.execute(sql, colValues)
                    rows2 = cursor.fetchone()
                    if rows2 is not None and len(rows2)==3:
                        avgValue = rows2[0]
                        minValue = rows2[1]
                        maxValue = rows2[2]
                        sql = "insert into SensorLong(sensorId, avgValue, minValue, maxValue, day, sixHour) values (?,?,?,?,?,?)"
                        colValues = [key, avgValue, minValue, maxValue, day_of_year, q]
                        cursor.execute(sql, colValues)
                conn.commit()
                cursor.close()
                self.ctx.closeDatabase(conn)
                self.ctx.dblock.release()

            # camera post processing
            for pid in self.extAppInProgress.keys():
                if self.extAppInProgress[pid][1].poll() is None:
                    outStrg, errStrg = self.extAppInProgress[pid][1].communicate()
                    if len(outStrg) > 0:
                        self.log.debug("CMD [%s] stdout: %s" % (self.extAppInProgress[pid][2], outStrg))
                    if len(errStrg) > 0:
                        self.log.error(("CMD [%s] stderr: %s" % (self.extAppInProgress[pid][2], errStrg)))
                    del self.extAppInProgress[pid]
                else:
                    runtime = (now-self.extAppInProgress[pid][0]).seconds
                    if runtime > 600:
                        self.log.warn("[CUNO] Process with pid %d is running since %d seconds"
                                      % (pid, runtime))
                    if runtime > 2000:
                        # give up
                        del self.extAppInProgress[pid]


            # camera snapshot
            camData = {}
            for camId in self.ctx.camera.keys():
                ipCam = self.ctx.camera[camId]
                if ipCam.timelapseEnabled:
                    url = ipCam.snapshotAddress
                    cam = IPCamera()
                    path = ipCam.timelapseJPGs
                    fName = time.strftime('%Y%m%d-%H%M%S', time.gmtime()) + '.jpg'
                    cam.saveSnapshot(url, os.path.join(path, fName))

                    # camera hourly
                    if quarter == 0:
                        self.log.debug("[Poller] Encoding hourly timelapse videos")
                        params = {}
                        params['output'] = ipCam.timelapseMP4
                        params['jpgDir'] = path
                        params['hours'] = 6
                        camData[url] = params
            if quarter == 0 and len(camData.keys())>0:
                # TODO
                cmd = '/root/dev/prc/extApps/generateMP4.sh'
                fd, path = tempfile.mkstemp()
                with os.fdopen(fd, 'w') as tmpFile:
                    tmpFile.write(json.dumps(camData))
                try:
                    p = subprocess.Popen([cmd, path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.extAppInProgress[p.pid] = [datetime.now(), p, cmd]
                except Exception, e:
                    self.log.error("[Poller] Error executing shell command %s: Reason %s" % (cmd, e))
                    self.log.debug("[Poller] Params were %s", json.dumps(camData))


            # backup
            nextBackup-=1
            if nextBackup == 0:
                nextBackup = 96
                self.backupToPeer()

            # alive check for threads
            nowUpdated = datetime.now()
            self.ctx.threadMonitor[self.__class__.__name__] = nowUpdated
            self.ctx.checkThreads(nowUpdated)

            # adjust the waiting time, otherwise we will deviate from the hourly quarter with each loop
            timeNeeded = (datetime.now() - now).seconds
            if timeNeeded < Poller.WAITSECS:
                self.wakeup.wait(Poller.WAITSECS - timeNeeded)
                self.wakeup.clear()
        self.log.info("Terminating Poll Thread")


    def backupToPeer(self):
        if not(self.cfg.hasKey(self.cfg.scope['general'], 'peerBackup')):
            return
        backupCfg = self.cfg.general.peerBackup
        if len(backupCfg)<2:
            self.log.warn("[Poller] Peer Backup not configured properly")
            return
        if len(backupCfg)==2:
            return

        self.log.info("[Poller] Start Backup")
        sslCert = self.cfg.general.clientCertFile
        # build file list
        baseDir = backupCfg[0]
        backupFileList = []
        for item in backupCfg[2:]:
            path = os.path.join(baseDir, item)
            if os.path.isdir(path):
                for root, directories, files in os.walk(path):
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        backupFileList.append(filepath)
            else:
                backupFileList.append(path)

        # check for peers that are configured for backup
        backupPeers={}
        for p in self.ctx.peer.keys():
            if self.ctx.peer[p].roamingAddress is not None:
                dct = {}
                dct[FN.FLD_CMD] = FN.CMD_CANBACKUP
                dct[FN.FLD_SERVERID] = self.serverId
                resultDct = None
                r = requests.post(self.ctx.peer[p].roamingAddress, json=dct, verify=sslCert)
                if r.status_code == 200:
                    resultDct = json.loads(r.text)
                    if resultDct[FN.FLD_STATUS] == FN.ok:
                        backupPeers[self.ctx.peer[p].roamingAddress] = resultDct[FN.FLD_BACKUP]
        if len(backupPeers.keys()) == 0:
            self.log.warn("[Poller] Backup not successful - no peers for backup found")
            return

        #backupDir = os.path.join(baseDir, backupCfg[1])
        for path in backupFileList:
            hash = self.md5ofFile(path)
            wrappedFile = None
            for addr in backupPeers.keys():
                remoteMD5 = backupPeers[addr]
                if not(item in remoteMD5 and remoteMD5[item] == hash):
                    if wrappedFile is None:
                        wrappedFile = self.wrapFile(path)
                    dct = {}
                    dct[FN.FLD_CMD] = FN.CMD_BACKUP
                    dct[FN.FLD_NAME] = item
                    dct[FN.FLD_SERVERID] = self.serverId
                    dct[FN.FLD_DATA] = wrappedFile
                    r = requests.post(addr, json=dct, verify=sslCert)
                    if r.status_code == 200:
                        resultDct = json.loads(r.text)
                    else:
                        self.log.warn("[Poller] Unable to backup file %s to host %s" % (item, addr))
        self.log.info("[Poller] End Backup")


    def md5ofFile(self, fileName):
        md5 = hashlib.md5()
        with open(str(fileName), 'rb') as file:
            buf = file.read()
            md5.update(buf)
        return md5.hexdigest()


    # zip file to temp file and return base 64 encoded
    def wrapFile(self, fileName):
        tmpFile = tempfile.mktemp()
        with ZipFile(tmpFile, 'w') as zip:
            zip.write(fileName)
        with open(tmpFile, "rb") as fl:
            b64Encoded = base64.b64encode(fl.read())
        os.remove(tmpFile)
        return b64Encoded

    def doTerminate(self):
        self.log.info("Received termination request for Poll Thread")
        self.terminate = True
        self.wakeup.set()


