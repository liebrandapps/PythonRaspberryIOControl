
from os.path import exists

class Sens18B20Wrapper:

    def __init__(self):
        pass

    def measure(self, sensorAddress):
        status = "fail"
        value = "0"
        fName = "/sys/bus/w1/devices/%s/w1_slave" % (sensorAddress)
        if exists(fName):
            tempFile = open(fName)
            txt = tempFile.read()
            tempFile.close()
            dta = txt.split("\n")[1].split(" ")[9]
            temp = float(dta[2:])
            temp = temp / 1000
            value = str(temp)
            status = "ok"
        return [status, value]