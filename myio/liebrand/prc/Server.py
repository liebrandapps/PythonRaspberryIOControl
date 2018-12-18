
import sys


from myio.liebrand.phd.server import Daemon, Server
from myio.liebrand.prc.Context import Context
from myio.liebrand.prc.local.Kerui import KeruiWrapper
from myio.liebrand.prc.PRCWebHandler import PRCWebHandler
from myio.liebrand.prc.PRCApiHandler import PRCApiHandler
from myio.liebrand.prc.Poller import Poller
from myio.liebrand.prc.remote.Cuno import Cuno
from myio.liebrand.prc.remote.MQTT import MQTTSubscriber, MQTTPublisher


def terminate(sigNo, stackFrame):
    if pollerThread is not None:
        pollerThread.doTerminate()
    if cunoThread is not None:
        cunoThread.doTerminate()
    if keruiThread is not None:
        keruiThread.doTerminate()
    if mqtt is not None:
        mqtt.stop()

if __name__ == '__main__':
    pollerThread = None
    cfgDict = {
        'general': {
            'certFile': ["String", ],
            'keyFile': ["String", ],
            'clientCertFile': ["String", ],
            'serverId' : ["String", ],
            'netioCount' : ["Integer", 0],
            'hms100tCount' : ["Integer", 0],
            'hms100tfCount' : ["Integer", 0],
            'ksh300Count' : ["Integer", 0],
            'fs20SensorCount' : ["Integer", 0],
            'cameraCount' : ["Integer", 0],
            'rpiCam': ["Integer", 0],
            'bmp180': ["Integer", 0],
            'awningCount': ["Integer", 0],
            'chromeCastCount': ['Integer', 0],
            'keruiCount': ['Integer', 0],
            'zigbeeCount': ['Integer', 0],
            'address' : ["String", ],
            'addressNoSSL': ["String", ],
            'peerBackup' : ["Array", ]
        }
    }
    if len(sys.argv) > 1:
        todo = sys.argv[1]
        if todo in [ 'start', 'stop', 'restart', 'status' ]:
            pidFile = "/tmp/prc.pid"
            logFile = "/tmp/prc.log"
            d = Daemon(pidFile)
            d.startstop(todo, stdout=logFile, stderr=logFile)
    ctx = Context(cfgDict)
    status = ctx.getStatus()
    if not(status[0] and status[1] and status[2]):
        sys.exit(-1)
    sslConfig =[ ctx.getConfig().general_certFile, ctx.getConfig().general_keyFile ]
    pollerThread = Poller(ctx)
    pollerThread.start()
    cunoThread = Cuno(ctx)
    if cunoThread.enabled:
        cunoThread.start()
        for k in ctx.fs20.keys():
            ctx.fs20[k].wrapper.cuno=cunoThread
    else:
        cunoThread = None
    if len(ctx.kerui)>0:
        keruiThread = KeruiWrapper(ctx)
        keruiThread.start()
    else:
        keruiThread = None
    mqtt = MQTTSubscriber(ctx)
    if mqtt.enabled:
        mqtt.start()
        mqttPub = MQTTPublisher(mqtt)
        for k in ctx.zigbee.keys():
            ctx.zigbee[k].wrapper=mqttPub
    else:
        mqtt = None
    prcApiHandler = PRCApiHandler(ctx)
    prcWebHandler = PRCWebHandler(ctx)
    ctx.api = prcApiHandler
    s = Server(8020, [prcApiHandler, prcWebHandler, ], ctx.getLogger(), sslConfig=sslConfig)
    #serve http on 8019
    s.additionalHosts = {8019: [prcWebHandler, ]}
    s.ownSignalHandler(terminate)
    s.serve()



