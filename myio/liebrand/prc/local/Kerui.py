# https://www.liebrand.io/433-mhz-receiver-for-kerui-devices/
import errno
import os
import threading
import time
from datetime import datetime

import serial


class KeruiWrapper(threading.Thread):



    def __init__(self, ctx):
        threading.Thread.__init__(self)
        self.ctx = ctx
        self.log = ctx.getLogger()
        self.cfg = ctx.getConfig()
        self.terminate = False
        cfgDict = {
            "kerui" : {
                "enable": ['Boolean', False],
                "usbPort" : ['Array', "/dev/ttyUSB0", "/dev/ttyUSB1" ],
                "logUnknownDevices" : ['Boolean', True],
                "filterDuplicates" : ['Boolean', True],
                "forward": ['String', ]
            }
        }
        self.cfg.addScope(cfgDict)
        self.enabled = self.cfg.kerui_enable
        if self.enabled:
            self.usbPort = self.cfg.kerui_usbPort
            self.port = None
            self.lastHeardOf = {}
            self.unknownAddresses = []
            self.logUnknownDevices = self.cfg.kerui_logUnknownDevices
            self.filterDuplicates = self.cfg.kerui_filterDuplicates
            self.forward = self.cfg.kerui_forward

    def run(self):
        self.log.info("[KERUI] Starting Kerui Client")
        lastCleanup = datetime.now()
        self.ctx.threadMonitor[self.__class__.__name__] = lastCleanup
        portIdx = 0
        retryOnPorts = 10
        while not self.terminate:
            try:
                self.log.debug("[KERUI] Connecting receiver on port %s" % (self.usbPort[portIdx]))
                self.port = serial.Serial(self.usbPort[portIdx], baudrate=9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=30)
                while not self.terminate:
                    try:
                        code = str(self.port.readline())
                        now = datetime.now()
                        if len(code)>0:
                            code = code.strip()
                            knownDevice = False
                            for entityId in self.ctx.kerui.keys():
                                o = self.ctx.kerui[entityId]
                                if code in o.address:
                                    knownDevice = True
                                    if entityId in self.lastHeardOf and (now - self.lastHeardOf[entityId]).seconds<4:
                                        pass
                                    else:
                                        self.lastHeardOf[entityId] = now
                                        self.log.debug(o.message("!!!"))
                                        self.ctx.sdh.process(o, "!!!")
                                    break
                            if not knownDevice:
                                if self.forward is not None and len(self.forward):
                                    self.ctx.sdh.forward('kerui_', code, self.forward, "!!!")
                                if self.logUnknownDevices:
                                    if code not in self.unknownAddresses or not self.filterDuplicates:
                                        self.log.info("[KERUI] Unknown device ID %s", code)
                                        self.unknownAddresses.append(code)
                            if (now - lastCleanup).days > 0:
                                # reset unknown devices and lastHeardOf every 24 hours to prevent filling up memory
                                # implication is that unknown devices appear basically once a day
                                self.lastHeardOf = {}
                                self.unknownAddresses = []
                        self.ctx.threadMonitor[self.__class__.__name__] = now
                        self.ctx.checkThreads(now)
                    except TypeError:
                        time.sleep(1)
            except serial.SerialException, e:
                if e.args[0] == errno.ENOENT:
                    portIdx = (portIdx+1) % len(self.usbPort)
                    time.sleep(3)
                    retryOnPorts -= 1
                    if retryOnPorts == 0:
                        self.log.error("[KERUI] None of the configured USB Ports (%s) worked - terminating Kerui Client" %
                                       str(self.usbPort))
                        self.terminate = True
                        self.port = None
        del self.ctx.threadMonitor[self.__class__.__name__]
        self.log.info("[KERUI] Finishing Kerui Client")


    def doTerminate(self):
        if self.port is not None:
            self.port.close()
        self.terminate = True
