import json
import os

import serial
import re
from os.path import exists

class Fs20Wrapper:

    TRAILER = 'F'

    def __init__(self, fs20File):
        self.fs20File = fs20File
        self.state = {}
        self.load()
        self.cuno = None

    def constructCmd(self, address, cmdTxt, param=None):
        cmd = "00"
        if cmdTxt.upper()=="ON":
            cmd="10"
        elif cmdTxt.upper()=="OFF":
            cmd="00"
        elif cmdTxt=="startProg":
            cmd="16"
        elif cmdTxt=="stepDown":
            cmd="14"
        elif cmdTxt=="stepUp":
            cmd="13"
        elif cmdTxt == "on_off":
            cmd = "39"
        cmdString = address + cmd
        if param is not None:
            cmdString += param
        return cmdString

    def sendSerial(self, payload):
        device = "/dev/ttyS0"
        port = serial.Serial(device, baudrate=9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=3)
        sndStrg="02"
        if len(payload)==8:
            sndStrg += "05"
        else:
            sndStrg += "06"
        sndStrg += "F1" + payload
        seq = re.findall(r'.{1,2}',sndStrg,re.DOTALL)
        string=""
        for val in seq:
            string = string + chr(int(val,16))
        try:
            snd= ":".join("{:02x}".format(ord(c)) for c in string)
            port.write(string)
            rcv= ":".join("{:02x}".format(ord(c)) for c in port.read(4))
        except ValueError as e:
            print e
            rcv=str(e)
        port.close()
        return [snd, rcv]

    def sendCuno(self, payload):
        sndStrg = Fs20Wrapper.TRAILER + payload
        self.cuno.addCommand(sndStrg)

    def send(self, address, cmd, param=None):
        # RPi 3 -> change from AMA0 to S0
        device = "/dev/ttyS0"
        #if os.path.exists('dev/ttyS0'):
        #    device = '/dev/ttyS0'
        port = serial.Serial(device, baudrate=9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=3)
        sndStrg="02"
        if param is None:
            sndStrg+="05"
        else:
            sndStrg+="06"
        sndStrg+="F1" + address
        if cmd.upper()=="ON":
            cmd="10"
        elif cmd.upper()=="OFF":
            cmd="00"
        elif cmd=="startProg":
            cmd="16"
        elif cmd=="stepDown":
            cmd="14"
        elif cmd=="stepUp":
            cmd="13"
        elif cmd == "on_off":
            cmd = "39"
        sndStrg += cmd
        if param is not None:
            sndStrg+=param
        seq = re.findall(r'.{1,2}',sndStrg,re.DOTALL)
        string=""
        for val in seq:
            string = string + chr(int(val,16))
        try:
            snd= ":".join("{:02x}".format(ord(c)) for c in string)
            port.write(string)
            rcv= ":".join("{:02x}".format(ord(c)) for c in port.read(4))
        except ValueError as e:
            print e
            rcv=str(e)
        port.close()
        return [snd, rcv]

    def switch(self, address, newValue):
        result = self.send(address, newValue, "00")
        if address in self.state:
            if newValue != self.state[address]:
                self.state[address] = newValue
                self.save()
        else:
            self.state[address] = newValue
            self.save()
        return [ result[0] + " -> " + result[1], "ok"]

    def status(self, address):
        if address in self.state:
            return self.state[address]
        else:
            return "off"

    #
    # shine turns on the actor for a couple of seconds
    # off is persistet as this reflects the status after
    # time is expired.
    #
    def shine(self, address, useCuno=False):
        payload = self.constructCmd(address, "on_off", param="91")
        if useCuno:
            self.sendCuno(payload)
            result = [payload, "ok"]
        else:
            result = self.sendSerial(payload)
        if address in self.state:
            if "off" != self.state[address]:
                self.state[address] = "off"
                self.save()
        else:
            self.state[address] = "off"
            self.save()
        return [ result[0] + " -> " + result[1], "ok"]

    def load(self):
        if exists(self.fs20File):
            with open(self.fs20File, 'r') as fp:
                self.state = json.load(fp)

    def save(self):
        with open(self.fs20File, 'w') as fp:
            json.dump(self.state, fp)

    def setCuno(self, cuno):
        self.cuno = cuno

