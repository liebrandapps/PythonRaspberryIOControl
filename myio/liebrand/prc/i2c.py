import time

import smbus



class i2cWrapper:

    address = 0x20 # I2C Adresse
    Pin= {"7": 0x80, "6":0x40, "5":0x20, "4":0x10,"3":0x08, "2":0x04, "1":0x02, "0":0x01, "all":0xff, "off":0x00}
    Bank= {"0" : 0x14, "1": 0x15, "ctl_0" : 0x00, "ctl_1" :0x01 }
    ON = "on"
    OFF = "off"

    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.bus.write_byte_data(i2cWrapper.address,i2cWrapper.Bank["ctl_0"], 0x00) # Bank A Ausgang
        self.bus.write_byte_data(i2cWrapper.address,i2cWrapper.Bank["ctl_1"], 0x00) # Bank B Ausgang

    def get(self, row):
        read = self.bus.read_byte_data(i2cWrapper.address,row)
        return read

    def set(self,row,data):
        write = self.bus.write_byte_data(i2cWrapper.address,row,data)
        read = self.get(row)
        return read

    def status(self, gpioId):
        i2cId = [str(int(gpioId) / 8), str(int(gpioId) % 8)]
        if self.get(i2cWrapper.Bank[i2cId[0]]) & (1 << int(i2cId[1])) > 0:
            state = i2cWrapper.ON
        else:
            state = i2cWrapper.OFF
        return state

    def switch(self, gpioId, newValue):
        status = "fail"
        i2cId = [str(int(gpioId) / 8), str(int(gpioId) % 8)]
        orgValue = self.get(i2cWrapper.Bank[i2cId[0]])

        if newValue.upper() == i2cWrapper.ON.upper():
            targetValue = orgValue + (1 << int(i2cId[1]))
        else:
            targetValue = orgValue & (255 - (1 << int(i2cId[1])))
        done = 3
        timeout = 1
        while (done > 0):
            # set the value
            self.set(i2cWrapper.Bank[i2cId[0]], targetValue)
            time.sleep(timeout)
            # did the relais actually flip?
            actualValue = self.get(i2cWrapper.Bank[i2cId[0]])
            if (actualValue == targetValue):
                status = "ok"
                break
            timeout = timeout * 2
            done -= 1
            if (done == 0):
                status = "bogus"
                # give up
                break
            time.sleep(0.5)
        if (self.get(i2cWrapper.Bank[i2cId[0]]) & (1 << int(i2cId[1]))) > 0:
            value = i2cWrapper.ON
        else:
            value = i2cWrapper.OFF
        return [value, status]
