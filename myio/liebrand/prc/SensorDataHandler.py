import json
import os
import subprocess
import tempfile
from datetime import datetime
import time
import hashlib
import sqlite3

from myio.liebrand.prc.FieldNames import FN


class SensorDataHandler:

    TOPIC_UPDATE = "update"
    KEY_SERVERID = "serverId"
    KEY_MSGTYPE = "msgType"
    KEY_TIMESTAMP = "timeStamp"

    def __init__(self, ctx):
        self.ctx = ctx
        self.cfg = ctx.cfg
        self.log = ctx.log
        self.serverId = self.cfg.general_serverId
        self.deviceLastEvent = {}
        self.pushNotify = ctx.getPushNotify()
        self.shellCmdInProgress = {}
        self.shellCmdLastEvent = {}


    #
    # handle the incoming sensor data:
    # + save in database
    # + send message
    # + trigger script
    #
    def process(self, device, value1, value2=None):
        now =datetime.now()
        tmpValue = str(value1)
        if tmpValue in device.ignore:
            return
        if value2 is not None:
            tmpValue = "%s | %s" % (str(value1), str(value2))
        m = hashlib.md5()
        m.update(device.entityId + tmpValue)
        md5 = m.hexdigest()
        #self.log.debug("%s %s %s" % (device.getId(), tmpValue, md5))
        #self.log.debug(self.deviceLastEvent)
        if md5 in self.deviceLastEvent and (now - self.deviceLastEvent[md5]).seconds < 15:
            return
        self.deviceLastEvent[md5] = now
        #self.log.debug(device.peerSensors)
        for d in device.peerSensors:
            m = hashlib.md5()
            m.update(d + tmpValue)
            md5 = m.hexdigest()
            #self.log.debug("%s %s %s" % (d, tmpValue, md5))
            self.deviceLastEvent[md5] = now
        # save to db
        conn = None
        cursor = None
        try:
            now = datetime.now()
            conn = self.ctx.openDatabase()
            cursor = conn.cursor()
            sql = "insert into PushSensorShort(sensorId, value1, value2, atTime) values (?, ?, ?, ?)"
            colValues = [device.entityId, value1, value2, now]
            cursor.execute(sql, colValues)
            conn.commit()
            cursor.close()
            self.ctx.closeDatabase(conn)
        except sqlite3.OperationalError as e:
            self.log.warn("[CUNO] Cannot write to db: %s" % e)
            if cursor is not None:
                cursor.close()
            if conn is not None:
                self.ctx.closeDatabase(conn)

        # send message
        if not device.disableNotify and self.ctx.fcm.isFCMEnabled:
            message = {}
            message[device.entityId] = {FN.FLD_VALUE : tmpValue,
                                    FN.FLD_TIMESTAMP : str(int(time.time() * 1000)),
                                    FN.FLD_CMD : "cuno"}
            message[SensorDataHandler.KEY_SERVERID] = self.serverId
            message[SensorDataHandler.KEY_MSGTYPE] = "evtUpdate"
            payload = self.pushNotify.buildDataMessage(SensorDataHandler.TOPIC_UPDATE, message)
            if device.prio > 1:
                self.pushNotify.addNotificationtoMessage(payload, device.getName('en'), "")
            self.pushNotify.pushMessage(payload, device.prio)

        # trigger script
        shellCmd = device.shellCmd
        if shellCmd is not None:
            shellCmd = shellCmd.split(':')
            m = hashlib.md5()
            m.update(shellCmd[0])
            md5=m.hexdigest()
            if md5 in self.shellCmdLastEvent:
                lastEvent = (now - self.shellCmdLastEvent[md5]).seconds
            else:
                lastEvent = 0
            self.shellCmdLastEvent[md5] = now
            params = {}
            params[device.entityId] = tmpValue
            params['lastEvent'] = lastEvent
            params['clientCertFile'] = self.cfg.general.clientCertFile
            params['address'] = self.cfg.general.address
            for entity in shellCmd[1:]:
                if entity.startswith('peer_'):
                    if entity in self.ctx.peer:
                        params[entity] = self.ctx.peer[entity].roamingAddress
                elif entity in self.ctx.switch or entity in self.ctx.fs20 or entity in self.ctx.netio230:
                    fields = { 'id' : entity, 'host' : self.cfg.general.address }
                    dct = {}
                    self.ctx.api.cmdStatus(fields, dct, self.cfg.general.address)
                    params[entity] = dct[entity]['status']
                else:
                    self.log.warn("[SDH] Could not resolve parameter %s for shell command of device %s" %
                                      (entity, device.getId()))
            fd, path = tempfile.mkstemp()
            with os.fdopen(fd, 'w') as tmpFile:
                tmpFile.write(json.dumps(params))
            try:
                p = subprocess.Popen([shellCmd[0], path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.shellCmdInProgress[p.pid] = [ datetime.now(), p, shellCmd ]
            except Exception, e:
                self.log.error("[SDH] Error executing shell command %s: Reason %s" % (shellCmd, e))


    def checkForLeftOverProcesses(self):
        # check for leftover shell cmds
        for pid in self.shellCmdInProgress.keys():
            if self.shellCmdInProgress[pid][1].poll() is None:
                outStrg, errStrg = self.shellCmdInProgress[pid][1].communicate()
                if len(outStrg) > 0:
                    self.log.debug("[SDH] CMD [%s] stdout: %s" % (self.shellCmdInProgress[pid][2], outStrg))
                if len(errStrg) > 0:
                    self.log.error(("[SDH] CMD [%s] stderr: %s" % (self.shellCmdInProgress[pid][2], errStrg)))
                del self.shellCmdInProgress[pid]
            else:
                now = datetime.now()
                runtime = (now - self.shellCmdInProgress[pid][0]).seconds
                if runtime > 30:
                    self.log.warn("[SDH] Process with pid %d is running since %d seconds"
                                  % (pid, runtime))
                if runtime > 45:
                    # give up
                    del self.shellCmdInProgress[pid]


