
# This module loads the Adafruit... py modules dynamically to read data from the BMP Hardware
# You need to copy Adafruit_BMP085.py and Adafruit_I2C.py to the root you the installation
# if the moduls cannot be loaded, the measure values will away be zero.

import sys

class BMP180Wrapper:

    def __init__(self):
        try:
            sys.path.append("./extApps")
            module = __import__("Adafruit_BMP085", fromlist=['BMP085'])
            self.bmpClass = getattr(module, 'BMP085')
        except ImportError, e:
            print "Adafruit Module is missing: " + e.message
            self.bmpClass = None

    def measure(self):
        if self.bmpClass is None:
            return [0.0, 0.0]
        bmp = self.bmpClass()
        return [bmp.readTemperature(), bmp.readPressure() / 100]

