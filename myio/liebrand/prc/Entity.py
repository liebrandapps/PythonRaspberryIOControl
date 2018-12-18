

#
# Extend your locales here
#
import json


class Entity:

    NAME = "name_%s"
    LOCALE = ["de", "en", "pl"]


    def __init__(self, cfgDict, cfg):
        self.entityId = cfgDict.keys()[0]
        for l in Entity.LOCALE:
            key = Entity.NAME % l
            cfgDict[self.entityId][key] = ["String", None]
        cfgDict[self.entityId]['shellCmd'] = ["String", None]
        cfgDict[self.entityId]['disableNotify'] = ["Boolean", False]
        cfgDict[self.entityId]['prio'] = ["Integer", 0]
        cfgDict[self.entityId]['peerSensors'] = ["Array", None ]
        cfgDict[self.entityId]['ignore'] = ["Array", None ]
        cfgDict[self.entityId]['googleActionVerbs'] = ["Array", None]
        cfgDict[self.entityId]['googleActionResponses'] = ["Array", None]
        cfg.addScope(cfgDict)
        self.shellCmd = getattr(cfg, '%s_shellCmd' % self.entityId)
        self.disableNotify = getattr(cfg, '%s_disableNotify' % self.entityId)
        self.prio = getattr(cfg, '%s_prio' % self.entityId)
        self.peerSensors = getattr(cfg, '%s_peerSensors' % self.entityId)
        self.ignore = getattr(cfg, '%s_ignore' % self.entityId)
        self.googleActionVerbs = getattr(cfg, '%s_googleActionVerbs' % self.entityId)
        self.googleActionResponses = getattr(cfg, '%s_googleActionResponses' % self.entityId)
        self.name = {}
        for l in Entity.LOCALE:
            key = Entity.NAME % l
            if getattr(cfg, '%s_%s' % (self.entityId, key)) is not None:
                self.name[l] = getattr(cfg, '%s_%s' % (self.entityId, key))
        self.wrapper = None

    def getName(self, locale):
        if locale in self.name:
            return self.name[locale]
        else:
            print self.entityId
            print self.name
            if len(self.name)>0:
                return self.name.itervalues().next()
            else:
                return("?")



class Peer(Entity):


    def __init__(self, index, cfg):
        cfgDict = {
            "peer_%d" % index : {
                'address': ["String", ],
                'roamingAddress': ["String", None],
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.address = getattr(cfg, '%s_address' % self.entityId)
        self.roamingAddress = getattr(cfg, '%s_roamingAddress' % self.entityId)

    def getAddress(self):
        return self.address

    def getRoamingAddress(self):
        return self.roamingAddress



class Switch(Entity):

    SECTION = "switch_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            Switch.SECTION % index : {
                'gpio': ["Integer", ],
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.gpio = getattr(cfg, '%s_gpio' % self.entityId)

    def getGPIO(self):
        return self.gpio



class FS20(Entity):

    SECTION = "fs20_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            FS20.SECTION % index : {
                'address': ["String", ],
                'useCuno': ["Boolean", False]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.address = getattr(cfg, '%s_address' % self.entityId)
        self.useCuno = getattr(cfg, '%s_useCuno' % self.entityId)

    def getAddress(self):
        return self.address

    def getUseCuno(self):
        return self.useCuno


class UltraSonic(Entity):

    SECTION = "ultrasonic_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            UltraSonic.SECTION % index : {
                'min': ["Integer", ],
                'max': ["Integer", ],
                'inverse': ["Boolean", False]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.min = getattr(cfg, '%s_min' % self.entityId)
        self.max = getattr(cfg, '%s_max' % self.entityId)
        self.inverse = getattr(cfg, '%s_inverse' % self.entityId)

    def getRange(self):
        return [self.min, self.max]

    def getInverse(self):
        return self.inverse

    def measure(self):
        return self.wrapper.measure()

class Sensor18B20(Entity):

    SECTION = "temperature_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            Sensor18B20.SECTION % index : {
                'min': ["Integer", ],
                'max': ["Integer", ],
                'address': ["String", ]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.min = getattr(cfg, '%s_min' % self.entityId)
        self.max = getattr(cfg, '%s_max' % self.entityId)
        self.address = getattr(cfg, '%s_address' % self.entityId)

    def getRange(self):
        return [self.min, self.max]

    def getAddress(self):
        return self.address

    def measure(self):
        return self.wrapper.measure(self.address)


class Netio230(Entity):

    SECTION = "netio_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            Netio230.SECTION % index : {
                'id': ["String", ],
                'address': ["String", ]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.address = getattr(cfg, '%s_address' % self.entityId).split(':')
        self.accessId = getattr(cfg, '%s_id' % self.entityId).split(':')

    def getAddress(self):
        return self.address

    def getAccessId(self):
        return self.accessId

    def status(self):
        return self.wrapper.getStatus(self.accessId, self.address)

    def switch(self, newValue):
        if newValue == "on":
            return self.wrapper.turnOn(self.accessId, self.address)
        else:
            return self.wrapper.turnOff(self.accessId, self.address)

class HMS100T(Entity):

    SECTION = "hms100t_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            HMS100T.SECTION % index : {
                'address': ["String", ]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.address = getattr(cfg, '%s_address' % self.entityId)

    def getAddress(self):
        return self.address


class HMS100TF(Entity):

    SECTION = "hms100tf_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            HMS100TF.SECTION % index : {
                'address': ["String", ]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.address = getattr(cfg, '%s_address' % self.entityId)

    def getAddress(self):
        return self.address

class KSH300(Entity):

    SECTION = "ksh300_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            KSH300.SECTION % index : {
                'address': ["String", ]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.address = getattr(cfg, '%s_address' % self.entityId)

    def getAddress(self):
        return self.address

class FS20Sensor(Entity):

    SECTION = "fs20Sensor_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            "fs20Sensor_%d" % index : {
                'address': ["String", ]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.address = getattr(cfg, '%s_address' % self.entityId)

    def getAddress(self):
        return self.address


class Camera(Entity):

    SECTION = "camera_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            Camera.SECTION % index: {
                'snapshotAddress': ["String", ],
                'streamingAddress': ["String", ],
                'enableTimelapse': ["Boolean", False],
                'enableStreaming': ["Boolean", False],
                'timelapseMP4': ["String", ],
                'timelapseCodec': ["String", ],
                'timelapseJPGs': ["String", ],
                'timelapseHours': ["Integer", 6]
            } }
        Entity.__init__(self, cfgDict, cfg)
        self.snapshotAddress = getattr(cfg, '%s_snapshotAddress' % self.entityId)
        self.timelapseEnabled = getattr(cfg, '%s_enableTimelapse' % self.entityId)
        self.streamingEnabled = getattr(cfg, '%s_enableStreaming' % self.entityId)
        if self.streamingEnabled:
            self.streamAddress = getattr(cfg, '%s_streamingAddress' % self.entityId)
        if self.timelapseEnabled:
            self.timelapseMP4 = getattr(cfg, '%s_timelapseMP4' % self.entityId)
            self.timelapseCodec = getattr(cfg, '%s_timelapseCodec' % self.entityId)
            self.timelapseJPGs = getattr(cfg, '%s_timelapseJPGs' % self.entityId)
            self.timelapseHours = getattr(cfg, '%s_timelapseHours' % self.entityId)

class RpiCam(Entity):

    SECTION = "rpicam_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            RpiCam.SECTION % index: {
                "resX": ["Integer", 2592],
                "resY": ["Integer", 1944]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.resX = getattr(cfg, "%s_resX" % self.entityId)
        self.resY = getattr(cfg, "%s_resY" % self.entityId)

class BMP180(Entity):

    SECTION = "bmp180_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            BMP180.SECTION % index: {
            }
        }
        Entity.__init__(self, cfgDict, cfg)


class Awning(Entity):

    SECTION ="awning_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            Awning.SECTION % index: {
                'address': ["String", ]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.address = getattr(cfg, '%s_address' % self.entityId)

class ChromeCast(Entity):

    SECTION = "chromeCast_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            ChromeCast.SECTION % index: {
                "friendlyName": ["String", ],
                "callName": ["String",]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.friendlyName = getattr(cfg, '%s_friendlyName' % self.entityId)
        self.callName = getattr(cfg, '%s_callName' % self.entityId)

class Kerui(Entity):

    SECTION = "kerui_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            Kerui.SECTION % index: {
                "address" : ["String", ]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.address = getattr(cfg, '%s_address' % self.entityId)

class Zigbee(Entity):

    SECTION = "zigbee_%d"

    def __init__(self, index, cfg):
        cfgDict = {
            Zigbee.SECTION % index: {
                "topic" : ["String", ],
                "suffix": ["String", "/set"]
            }
        }
        Entity.__init__(self, cfgDict, cfg)
        self.topic = getattr(cfg, "%s_topic" % self.entityId)
        self.suffix = getattr(cfg, "%s_suffix" % self.entityId)

    def switch(self, value):
        if value == 'on':
            self.turnOn()
        else:
            self.turnOff()

    def turnOn(self):
        dct = { 'state' : 'ON' }
        self.wrapper.publish(self.topic + self.suffix, json.dumps(dct))

    def turnOff(self):
        dct = { 'state' : 'OFF' }
        self.wrapper.publish(self.topic + self.suffix, json.dumps(dct))