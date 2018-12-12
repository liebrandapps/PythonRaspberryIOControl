import errno
import json
import select
import sqlite3
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
        self.sensorDataHandler = ctx.sdh
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

        self.sensorAddress = {}
        hms100t = ctx.hms100t
        for key in hms100t.keys():
            self.sensorAddress['HMS100T:' +hms100t[key].address] = hms100t[key]
        hms100tf = ctx.hms100tf
        for key in hms100tf.keys():
            self.sensorAddress['HMS100TF:' +hms100tf[key].address] = hms100tf[key]
        ksh300 = ctx.ksh300
        for key in ksh300.keys():
            self.sensorAddress['KSH300:' +ksh300[key].address] = ksh300[key]
        fs20Sensor = ctx.fs20Sensor
        for key in fs20Sensor.keys():
            self.sensorAddress['FS20Sensor:' +fs20Sensor[key].address] = fs20Sensor[key]



    def run(self):
        if not self.enabled:
            self.log.info("[CUNO] CUNO Client disabled")
            return
        self.log.info("[CUNO] Starting CUNO Client")
        self.isRunning = True
        reConCount = 1
        tn = None
        lastCmdSend = datetime.now()
        while not (self.terminate):
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
            self.sensorDataHandler.checkForLeftOverProcesses()

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
                self.sensorDataHandler.process(device, temp)
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
                self.sensorDataHandler.process(device, temp, value2=humidity)
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
                self.sensorDataHandler.process(device, temp, value2=humidity)
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
                self.sensorDataHandler.process(device, devSpec)
                self.log.debug("[CUNO] %s [%s] %s { %s }" % (device.getName("en"), deviceType, devSpec, x))
            else:
                if not (address in self.unknownDevices):
                    self.unknownDevices.append(address)
                    self.log.warn("[CUNO] Message %s from unknown FS20 device received: %s" % (x, address))

        if not handled:
            self.log.debug("[CUNO] Unhandled device message {x}" % x)



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



