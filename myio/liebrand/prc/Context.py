import sqlite3
import sys
import exceptions
import logging
import time
from logging.handlers import RotatingFileHandler
from os.path import join, exists, dirname, isdir
from os import access, W_OK, R_OK

from myio.liebrand.prc.Entity import Switch, FS20, UltraSonic, Sensor18B20, Netio230, HMS100T, HMS100TF, KSH300, \
    FS20Sensor, Peer, Camera, RpiCam, BMP180, Awning
from myio.liebrand.prc.Sens18B20 import Sens18B20Wrapper
from myio.liebrand.prc.config import Config
from myio.liebrand.prc.fs20 import Fs20Wrapper
from myio.liebrand.prc.i2c import i2cWrapper
from myio.liebrand.prc.local.Awning import AwningWrapper
from myio.liebrand.prc.local.BMP180 import BMP180Wrapper
from myio.liebrand.prc.local.Camera import CamModule
from myio.liebrand.prc.remote.Camera import IPCamera
from myio.liebrand.prc.remote.Netio230 import Netio230Wrapper
from myio.liebrand.prc.ultrasonic import UltraSonicWrapper
from myio.liebrand.prc.PushNotify import PushNotification


class Context:

    SECTION = "general"
    CONFIG_DIR = "./"
    CONFIG_FILE = "prc.ini"

    def __init__(self, initialConfig):
        self.cfgOk = False
        self.logOk = False
        self.dbOk = False
        path = join(Context.CONFIG_DIR, Context.CONFIG_FILE)
        self.log = None
        if not (exists(path)):
            self.printLogLine(sys.stderr,
                              "[IPFSSVR] No config file %s found at %s" % (Context.CONFIG_FILE, Context.CONFIG_DIR))
            return
        self.cfgOk = True
        self.cfg = Config(path, Context.SECTION)
        self.cfg.addScope(initialConfig)
        self.logOk = self.setupLogger()
        self.dbOk = self.setupDatabase()
        self.peer = {}
        self.switch = {}
        self.fs20 = {}
        self.ultrasonic = {}
        self.sensor18B20 = {}
        self.netio230 = {}
        self.hms100t = {}
        self.hms100tf = {}
        self.ksh300 = {}
        self.fs20Sensor = {}
        self.camera = {}
        self.rpiCam = {}
        self.bmp180 = {}
        self.awning = {}
        self.fcm = PushNotification(self)
        self.api = None
        self.setupDevices()

    def getStatus(self):
        return [self.cfgOk, self.logOk, self.dbOk]

    def getTimeStamp(self):
        return time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(time.time()))

    def printLogLine(self, fl, message):
        fl.write('%s %s\n' % (self.getTimeStamp(), message))
        fl.flush()

    def setupLogger(self):
        try:
            self.log = logging.Logger("PREBC")
            self.loghdl = RotatingFileHandler(self.cfg.logFileName, 'a', self.cfg.maxFilesize, 4)
            #self.loghdl = logging.FileHandler(cfg.logFileName)
            self.loghdl.setFormatter(logging.Formatter(self.cfg.msgFormat))
            self.loghdl.setLevel(self.cfg.logLevel)
            self.log.addHandler(self.loghdl)
            self.log.disabled = False
            self.initialLogLevel = self.cfg.logLevel
            self.debugLevel = False
            return True
        except exceptions.Exception, e:
            self.printLogLine(sys.stderr, "[PREBC] Unable to initialize logging. Reason: %s" % e)
            return False

    def setupDatabase(self):
        dbFile = self.cfg.database
        if not(exists(dbFile)):
            self.log.info("Database File <%s> does not exist" % dbFile)
            dbPath = dirname(dbFile)
            if not(isdir(dbPath)):
                self.log.error("Unable to create database as path <%s> does not exist." % dbPath)
            else:
                if not(access(dbPath, W_OK) and access(dbPath, R_OK)):
                    self.log.error("Insufficient permissions for path <%s> to have a database file" % dbPath)
                else:
                    # if we made it until this point, we are good to create a database
                    createScripts = join(self.cfg.sqlScripts, "createTables.sql")
                    if not (exists(createScripts)):
                        self.log.error("SQL Script File %s does not exists" % (createScripts,))
                    else:
                        with open(createScripts) as f:
                            content = f.readlines()
                        lines = [x.strip() for x in content]
                        try:
                            conn = sqlite3.connect(dbFile)
                            self.log.info("Created database %s" % dbFile)
                            cur = conn.cursor()
                            for l in lines:
                                if l.startswith('#'):
                                    continue
                                sql = l
                                cur.execute(l)
                            self.log.info("Created tables - database is now ready to use.")
                            self.dbname = dbFile
                            return True
                        except sqlite3.Error as e:
                            self.log.error("Exception setting up database %s: %s" % (dbFile, e))
                        finally:
                            conn.close()
            return False
        self.dbname = dbFile
        return True


    def getLogger(self):
        return self.log

    def getConfig(self):
        return self.cfg

    def getPushNotify(self):
        return self.fcm

    def openDatabase(self):
        conn = None
        try:
            conn = sqlite3.connect(self.dbname, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            #self.log.debug("Opened databse %s" % self.dbname)
        except sqlite3.Error as e:
            self.log.error("Exception opening database %s: %s" % (self.dbname, e))
        return conn

    def closeDatabase(self, conn):
        if conn is not None:
            conn.close()

    def setupDevices(self):
        switchCount = self.cfg.switchCount
        fs20Count = self.cfg.fs20Count
        ultrasonicCount = self.cfg.ultrasonicCount
        temperatureCount = self.cfg.temperatureCount
        netioCount = self.cfg.general_netioCount
        hms100tCount = self.cfg.general_hms100tCount
        hms100tfCount = self.cfg.general_hms100tfCount
        ksh300Count = self.cfg.general_ksh300Count
        fs20SensorCount = self.cfg.general_fs20SensorCount
        cameraCount = self.cfg.general_cameraCount
        rpiCamCount = self.cfg.general_rpiCam
        bmp180Count = self.cfg.general_bmp180
        awningCount = self.cfg.general_awningCount
        self.cfg.setSection(Config.SECTIONS[Config.GENERAL])


        # peer is not really a device ... anyhow
        peerCount = self.cfg.peerCount
        for index in range(peerCount):
            pr = Peer(index + 1, self.cfg)
            self.peer[pr.entityId] = pr

        if switchCount>0:
            i2c = i2cWrapper()
            for index in range(switchCount):
                sw = Switch(index + 1, self.cfg)
                sw.wrapper=i2c
                self.switch[sw.entityId] = sw

        if fs20Count>0:
            for index in range(fs20Count):
                fs = FS20(index + 1, self.cfg)
                fs.wrapper=Fs20Wrapper(self.cfg.fs20Data)
                self.fs20[fs.entityId] = fs

        if ultrasonicCount>0:
            usWrapper = UltraSonicWrapper()
            for index in range(ultrasonicCount):
                wl = UltraSonic(index + 1, self.cfg)
                wl.wrapper=usWrapper
                self.ultrasonic[wl.entityId] = wl

        if temperatureCount>0:
            tempWrapper = Sens18B20Wrapper()
            for index in range(temperatureCount):
                t = Sensor18B20(index + 1, self.cfg)
                t.wrapper=tempWrapper
                self.sensor18B20[t.entityId] = t

        if netioCount>0:
            netioWrapper = Netio230Wrapper()
            for index in range(netioCount):
                n = Netio230(index + 1, self.cfg)
                n.wrapper=netioWrapper
                self.netio230[n.entityId] = n

        for index in range(hms100tCount):
            h = HMS100T(index+1, self.cfg)
            self.hms100t[h.entityId] = h

        for index in range(hms100tfCount):
            h = HMS100TF(index+1, self.cfg)
            self.hms100tf[h.entityId] = h

        for index in range(ksh300Count):
            k = KSH300(index+1, self.cfg)
            self.ksh300[k.entityId] = k

        for index in range(fs20SensorCount):
            f = FS20Sensor(index+1, self.cfg)
            self.fs20Sensor[f.entityId] = f

        if cameraCount>0:
            cameraWrapper = IPCamera()
            for index in range(cameraCount):
                c = Camera(index+1, self.cfg)
                c.wrapper=cameraWrapper
                self.camera[c.entityId] = c

        for index in range(rpiCamCount):
            c = RpiCam(index+1, self.cfg)
            c.wrapper=CamModule(c.resX, c.resY)
            self.rpiCam[c.entityId] = c

        for index in range(bmp180Count):
            c = BMP180(index+1, self.cfg)
            c.wrapper=BMP180Wrapper()
            self.bmp180[c.entityId] = c

        if awningCount>0:
            awningWrapper = AwningWrapper()
            for index in range(awningCount):
                o = Awning(index+1, self.cfg)
                o.wrapper = awningWrapper
                self.awning[o.entityId] = o



