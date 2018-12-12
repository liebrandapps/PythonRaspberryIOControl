# https://www.liebrand.io/433-mhz-receiver-for-kerui-devices/
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
                "usbPort" : ['String', "/dev/ttyUSB0" ],
                "logUnknownDevices" : ['Boolean', True]
            }
        }
        self.cfg.addScope(cfgDict)
        self.usbPort = self.cfg.kerui_usbPort
        self.port = None
        self.lastHeardOf = {}
        self.unknownAddresses = []
        self.logUnknownDevices = self.cfg.kerui_logUnknownDevices

    def send(self, address, cmd):
        snd = ""
        port = serial.Serial("/dev/ttyUSB0", baudrate=9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=3)
        try:
            time.sleep(2)
            while port.inWaiting() > 0:
                port.read(1)
            snd = "TFF" + address + "F0" + cmd + "$"
            port.write(snd)
            rcv = "Sent: " + snd
            time.sleep(.5)
        except ValueError as e:
            print e
            rcv=str(e)
        port.close()
        return [snd, rcv]

    def run(self):
        self.log.info("[KERUI] Starting Kerui Client")
        self.port = serial.Serial(self.usbPort, baudrate=9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=3)
        while not self.terminate:
            code = str(self.port.readline())
            if len(code)>0:
                code = code.strip()
                now = datetime.now()
                knownDevice = False
                for entityId in self.ctx.kerui.keys():
                    o = self.ctx.kerui[entityId]
                    if code == o.address:
                        knownDevice = True
                        if entityId in self.lastHeardOf and (now - self.lastHeardOf[entityId]).seconds<4:
                            pass
                        else:
                            self.lastHeardOf[entityId] = now
                            self.ctx.sdh.process(o, "!!!")
                        break
                if not knownDevice and self.logUnknownDevices:
                    if code not in self.unknownAddresses:
                        self.log.info("[KERUI] Unknown device ID %s", code)
                        self.unknownAddresses.append(code)

        self.log.info("[KERUI] Finishing Kerui Client")


    def doTerminate(self):
        self.port.close()
        self.terminate = True
