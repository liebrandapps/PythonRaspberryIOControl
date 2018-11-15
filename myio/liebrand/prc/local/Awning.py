# https://www.liebrand.io/automating-sunblinds-the-solution-2-2/

import time

import serial


class AwningWrapper:

    cmdDriveIn = "F0101"
    cmdDriveOut = "F0F0F"
    cmdStop = "FFFFF"

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
