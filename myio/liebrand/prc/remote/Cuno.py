import errno
import json
import select
import subprocess
import tempfile
import threading
import telnetlib
import traceback

import hashlib
from datetime import datetime
import time
import socket
import sys
import os

from myio.liebrand.prc import PRCApiHandler
from myio.liebrand.prc.FieldNames import FN


class Cuno(threading.Thread):

    cfgDict = { "cuno" : {
                'enable': ["Boolean", "no"],
                'host' : ["String", ],
                'port' : ["Integer", 2323],
                'repeat' : ["Integer", 1],
                'ignore': ["Array", []]
            }
    }

    TOPIC_UPDATE = "update"
    KEY_SERVERID = "serverId"
    KEY_MSGTYPE = "msgType"
    KEY_TIMESTAMP = "timeStamp"


    DVC_VALUES = 1
    DVC_STATUS = 2
    DVC_2VALUES = 3
    DVC_EVENT = 4


    def __init__(self, ctx):
        threading.Thread.__init__(self)
        self.ctx = ctx
        self.log = ctx.getLogger()
        self.cfg = ctx.getConfig()
        self.pushNotify = ctx.getPushNotify()
        self.cfg.addScope(Cuno.cfgDict)
        self.enabled = self.cfg.cuno.enable
        if not self.enabled:
            return
        self.host = self.cfg.cuno_host
        self.port = self.cfg.cuno_port
        self.repeat = self.cfg.cuno_repeat
        if self.repeat < 1:
            self.repeat = 1
        self.ignore = self.cfg.cuno_ignore
        self.serverId = self.cfg.general_serverId
        self.terminate = False
        self.wakeup = threading.Event()
        self.controlPipe = os.pipe()
        self.cmdQueue = []
        self.isRunning = False
        self.unknownDevices = []
        self.shellCmdInProgress = {}
        self.shellCmdLastEvent = {}
        self.deviceLastEvent = {}
        self.sensorAddress = {}
        hms100t = ctx.getHMS100T()
        for key in hms100t.keys():
            self.sensorAddress['HMS100T:' +hms100t[key].getAddress()] = hms100t[key]
        hms100tf = ctx.getHMS100TF()
        for key in hms100tf.keys():
            self.sensorAddress['HMS100TF:' +hms100tf[key].getAddress()] = hms100tf[key]
        ksh300 = ctx.getKSH300()
        for key in ksh300.keys():
            self.sensorAddress['KSH300:' +ksh300[key].getAddress()] = ksh300[key]
        fs20Sensor = ctx.getFS20Sensor()
        for key in fs20Sensor.keys():
            self.sensorAddress['FS20Sensor:' +fs20Sensor[key].getAddress()] = fs20Sensor[key]



    # ok - we run the telnet client with a timeout of 4 seconds,
    # it means we must wait for a shut down at max 4 seconds.
    # we query the device 900 times per hour then
    # we want to reconnect once per hour
    def run(self):
        if not self.enabled:
            self.log.info("[CUNO] CUNO Client disabled")
            return
        self.log.info("[CUNO] Starting CUNO Client")
        self.isRunning = True
        reConCount = 1
        tn = None
        lastCmdSend = datetime.now()
        while (not (self.terminate)):
            reConCount = reConCount - 1
            if reConCount == 0:
                waitTime = 20
                self.log.debug(
                    "[CUNO] (RE-)Connecting to CUNO Device at Host [%s], Port [%d]" % (self.host, self.port))
                if not (tn is None):
                    tn.close()
                try:
                    tn = telnetlib.Telnet(self.host, self.port)
                    reConCount = 900
                    tn.write("X21\n")
                except socket.timeout:
                    self.log.debug("[CUNO] Timeout while connecting to CUNO Device, will retry soon")
                    reConCount = 1
                    self.wakeup.wait(waitTime)
                    self.wakeup.clear()
                    waitTime = waitTime + 20
                    continue
                except socket.error, (value, message):
                    if value == 148:
                        self.log.error(
                            "[CUNO] No route to CUNO Device. Is the device running at address %s:%d ?" % (
                            self.host, self.port))
                    else:
                        self.log.error("[CUNO] %s" % (message))
                    self.terminate = True
                    continue
            # check for leftover shell cmds
            for pid in self.shellCmdInProgress.keys():
                if self.shellCmdInProgress[pid][1].poll() is None:
                    outStrg, errStrg = self.shellCmdInProgress[pid][1].communicate()
                    if len(outStrg) > 0:
                        self.log.debug("CMD [%s] stdout: %s" % (self.shellCmdInProgress[pid][2], outStrg))
                    if len(errStrg) > 0:
                        self.log.error(("CMD [%s] stderr: %s" % (self.shellCmdInProgress[pid][2], errStrg)))
                    del self.shellCmdInProgress[pid]
                else:
                    now = datetime.now()
                    runtime = (now-self.shellCmdInProgress[pid][0]).seconds
                    if runtime > 30:
                        self.log.warn("[CUNO] Process with pid %d is running since %d seconds"
                                      % (pid, runtime))
                    if runtime > 45:
                        # give up
                        del self.shellCmdInProgress[pid]
            #
            try:
                fds = [tn.fileno(), self.controlPipe[0]]
                try:
                    ready = select.select(fds, [], [], 60)
                except select.error, (_errno, _strerror):
                    if _errno == errno.EINTR:
                        continue
                    else:
                        raise
                if len(ready[0]) == 0:
                    # timeout
                    pass
                elif tn.fileno() in ready[0]:
                    xx = tn.read_very_eager()
                    if len(xx) > 0:
                        # self.log.debug(xx)
                        for x in xx.split('\n'):
                            if len(x) != 0:
                                x = x.rstrip('\n').rstrip('\r')
                                self.parse(x)
                                #if resp is not None:
                                #    tn.write(resp)
                elif self.controlPipe[0] in ready[0]:
                    os.read(self.controlPipe[0], 1)
                    if self.terminate:
                        continue
                while len(self.cmdQueue) > 0:
                    dta = self.cmdQueue.pop(0)
                    delta = datetime.now() - lastCmdSend
                    if delta.seconds < 2:
                        time.sleep(2 - delta.seconds)
                    self.log.debug("[CUNO] Sending command [%s]" % (dta.rstrip('\n').rstrip('\r')))
                    rpt = self.repeat
                    while rpt > 0:
                        rpt = rpt - 1
                        tn.write(dta)
                    lastCmdSend = datetime.now()

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print sys.exc_info()
                traceback.print_exc()
                tmp = os.path.split(exc_tb.tb_frame.f_code.co_filename)
                if len(tmp) > 1:
                    fname = tmp[1]
                else:
                    fname = "?"
                self.log.error("[CUNO] Exception [%s] at %s:%d" % (exc_type, fname, exc_tb.tb_lineno))
                tn.close()
                reConCount = 1

        self.log.info("[CUNO] Finishing CUNO Client")
        self.isRunning = False

    def parse(self, x):
        deviceId = x[0] + x[6]
        hc1 = x[1:3]
        hc2 = x[3:5]
        status = x[5]
        addrFS20 = x[5:7]
        devSpec = ""
        handled = False

        if deviceId == "H1":
            handled = True
            deviceType = "HMS100T"
            temp = float(int(x[9:11] + x[7:9])) / 10
            if int(status) > 7:
                temp = temp * (-1)
            devSpec = str(temp) + " C"
            address = hc1 + hc2
            if address in self.ignore:
                return
            if (deviceType + ':' + address) in self.sensorAddress:
                device = self.sensorAddress[deviceType + ':' + address]
                self.process(device, temp)
                self.log.debug("[CUNO] %s [%s] %s { %s }" % (device.getName("en"), deviceType, devSpec, x))
            else:
                if not(address in self.unknownDevices):
                    self.unknownDevices.append(address)
                    self.log.warn("[CUNO] Message %s from unknown HMS100T device received: %s" % (x, address))

        if deviceId == "H0":
            handled = True
            deviceType = "HMS100TF"
            temp = float(x[10] + x[7] + x[8]) / 10
            if int(status) > 7:
                temp = temp * (-1)
            humidity = float(x[11:13])
            devSpec = str(temp) + " C, " + str(humidity) + "%"
            address = hc1 + hc2
            if address in self.ignore:
                return
            if (deviceType + ':' + address) in self.sensorAddress:
                device = self.sensorAddress[deviceType + ':' + address]
                self.process(device, temp, value2=humidity)
                self.log.debug("[CUNO] %s [%s] %s { %s }" % (device.getName("en"), deviceType, devSpec, x))
            else:
                if not(address in self.unknownDevices):
                    self.unknownDevices.append(address)
                    self.log.warn("[CUNO] Message %s from unknown HMS100TF device received: %s" % (x, address))

        if deviceId[0] == "K":
            handled = True
            address = "K" + x[2]
            if address in self.ignore:
                return
            deviceType = "KSH300"
            humidity = float(x[7] + x[8] + "." + x[5])
            temp = float(x[6] + x[3] + "." + x[4])
            if int(x[1]) > 7:
                temp = temp * (-1)
            devSpec = str(temp) + " Grad, " + str(humidity) + "%"
            if (deviceType + ':' + address) in self.sensorAddress:
                device = self.sensorAddress[deviceType + ':' + address]
                self.process(device, temp, value2=humidity)
                self.log.debug("[CUNO] %s [%s] %s { %s }" % (device.getName("en"), deviceType, devSpec, x))
            else:
                if not (address in self.unknownDevices):
                    self.unknownDevices.append(address)
                    self.log.warn("[CUNO] Message %s from unknown KSH300 device received: %s" % (x, address))

        if deviceId[0] == "F":
            handled = True
            address = hc1 + hc2 + addrFS20
            if address in self.ignore:
                return
            deviceType = "FS20Sensor"
            if x[7] == "0":
                devSpec = "off"
            else:
                devSpec = "on"
            if (deviceType + ':' + address) in self.sensorAddress:
                device = self.sensorAddress[deviceType + ':' + address]
                self.process(device, devSpec)
                self.log.debug("[CUNO] %s [%s] %s { %s }" % (device.getName("en"), deviceType, devSpec, x))
            else:
                if not (address in self.unknownDevices):
                    self.unknownDevices.append(address)
                    self.log.warn("[CUNO] Message %s from unknown FS20 device received: %s" % (x, address))

        if not handled:
            self.log.debug("[CUNO] Unhandled device message {x}" % x)


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
            return;
        if value2 is not None:
            tmpValue = "%s | %s" % (str(value1), str(value2))
        m = hashlib.md5()
        m.update(device.getId() + tmpValue)
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
            #self.deviceLastEvent[md5] = now
        # save to db
        now = datetime.now()
        conn = self.ctx.openDatabase()
        cursor = conn.cursor()
        sql = "insert into PushSensorShort(sensorId, value1, value2, atTime) values (?, ?, ?, ?)"
        colValues = [device.getId(), value1, value2, now]
        cursor.execute(sql, colValues)
        conn.commit()
        cursor.close()
        self.ctx.closeDatabase(conn)

        # send message
        if not device.disableNotify:
            message = {}
            message[device.getId()] = {FN.FLD_VALUE : tmpValue,
                                    FN.FLD_TIMESTAMP : str(int(time.time() * 1000)),
                                    FN.FLD_CMD : "cuno"}
            message[Cuno.KEY_SERVERID] = self.serverId
            message[Cuno.KEY_MSGTYPE] = "evtUpdate"
            payload = self.pushNotify.buildDataMessage(Cuno.TOPIC_UPDATE, message)
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
            params[device.getId()] = tmpValue
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
                    self.log.warn("[CUNO] Could not resolve parameter %s for shell command of device %s" %
                                      (entity, device.getId()))
            fd, path = tempfile.mkstemp()
            with os.fdopen(fd, 'w') as tmpFile:
                tmpFile.write(json.dumps(params))
            try:
                p = subprocess.Popen([shellCmd[0], path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.shellCmdInProgress[p.pid] = [ datetime.now(), p, shellCmd ]
            except Exception, e:
                self.log.error("[CUNO] Error executing shell command %s: Reason %s" % (shellCmd, e))


    def doTerminate(self):
        os.write(self.controlPipe[1], 'x')
        self.terminate = True
        self.wakeup.set()

    def runs(self):
        return (self.isRunning)

    def addCommand(self, cmd):
        self.log.info("Queued Command %s" % (cmd))
        self.cmdQueue.append(cmd + "\r\n")
        os.write(self.controlPipe[1], 'x')



