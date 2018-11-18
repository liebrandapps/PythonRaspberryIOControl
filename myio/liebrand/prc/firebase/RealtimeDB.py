
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db



class RealtimeDB:

    def __init__(self, ctx):
        cfgDict = {
            "realtimeDB" : {
                "enable": ["Boolean", False],
                "databaseUrl": ["String",],
                "serviceAccountFile": ["String",],
                "more": ["String", "more"],
                "less": ["String", "less"],
                "equal": ["String", "equal"],
                "googleActionParameters" : ["Array", None]
            }
        }
        ctx.cfg.addScope(cfgDict)
        self.enabled = ctx.cfg.realtimeDB_enable
        if not(self.enabled):
            ctx.log.info("[RDB] Firebase Realtime DB not enabled in config.")
            return
        self.databaseUrl = ctx.cfg.realtimeDB_databaseUrl
        self.serviceAccountFile = ctx.cfg.realtimeDB_serviceAccountFile
        self.more = ctx.cfg.realtimeDB_more
        self.less = ctx.cfg.realtimeDB_less
        self.equal = ctx.cfg.realtimeDB_equal
        cred = credentials.Certificate(self.serviceAccountFile)
        firebase_admin.initialize_app(cred, {
            'databaseURL': self.databaseUrl
        })
        if len(ctx.cfg.realtimeDB_googleActionParameters)>0:
            ref = db.reference('prc')
            if ref is None:
                self.initialize()
            d = {}
            ctx.cfg.setSection("realtimeDB")
            for k in ctx.cfg.realtimeDB_googleActionParameters:
                d[k] = ctx.cfg.readValue(k)
            ref.update(d)
        ctx.log.info("[RDB] Firebase Realtime DB initialized.")

    def initialize(self):
        ref = db.reference('/')
        ref.set({ "prc" : {
                "fcmToken" : "",
                "fcmUrl" : ""
            }
        })

    def updateToken(self, token, url, host):
        ref = db.reference('prc')
        if ref is None:
            self.initialize()
        ref.update({
            'fcmToken': token,
            'fcmUrl' : url,
            'host' : host
        })

    def updateSensorTH(self, sensorName, value, response=None):
        dct = { sensorName : {} }
        ref = db.reference('prc')
        dct[sensorName]['temperature'] = value[0]
        if len(value) == 3:
            dct[sensorName]['humidity'] = value[1]
        if response is not None:
            dct[sensorName]['response'] = response
        ref.update(dct)

    def updateSensorT(self, sensorName, value, response=None):
        ref = db.reference('prc')
        ref.update({
            sensorName : {
                'temperature' : value
            }
        })

    def updateSensorS(self, sensorName, sensorId, value,  ago, response=None):
        dct = { sensorName : {} }
        ref = db.reference('prc')
        dct[sensorName][sensorId] = { 'value' : value, 'ago' : ago}
        if response is not None:
            dct[sensorName]['response'] = response
        ref.update(dct)