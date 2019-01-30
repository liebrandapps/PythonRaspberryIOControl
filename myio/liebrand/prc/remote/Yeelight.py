

from yeelight import Bulb, discover_bulbs





class YeelightWrapper:


    def __init__(self):
        pass


    def turnOn(self, address):
        ip = self.getIP(address)
        bulb = Bulb(ip)
        bulb.turn_on()

    def turnOff(self, address):
        ip = self.getIP(address)
        bulb = Bulb(ip)
        bulb.turn_off()

    def discover(self):
        return discover_bulbs()

    def status(self, address):
        ip = self.getIP(address)
        bulb = Bulb(ip)
        prp = bulb.get_properties()
        return prp['power']

    def getIP(self, address):
        if address.startswith('0x'):
            bulbs = self.discover()
            for b in bulbs:
                if b['capabilities']['id'] == address:
                    return b['ip']
        else:
            return address