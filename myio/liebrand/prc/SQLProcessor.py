import time
from datetime import datetime, timedelta
import threading


class SQLProcessor(threading.Thread):

    CMD_PUSHSENSORLONG = "1"
    CMD_SQL = "2"
    CMD_SQLMULTI = "3"

    def __init__(self, ctx):
        threading.Thread.__init__(self, name="SQL Processor")
        self.ctx = ctx
        self.sqlQueue = []
        self.event = threading.Event()
        self.terminate = False
        self.log = ctx.log

    def run(self):
        self.log.info("[SQL] Starting SQL Processor")
        self.ctx.threadMonitor[self.__class__.__name__] = datetime.now()
        while not self.terminate:
            self.event.wait()
            self.event.clear()
            if self.terminate:
                break

            now = datetime.now()
            while len(self.sqlQueue) > 0:
                self.ctx.acquireDBLock(__file__)
                sql = self.sqlQueue.pop(0)
                cmd = sql[0]
                if cmd == SQLProcessor.CMD_PUSHSENSORLONG:
                    self.cmdPushSensorLong()
                if cmd == SQLProcessor.CMD_SQL:
                    self.cmdInsert(sql[1], sql[2])
                if cmd == SQLProcessor.CMD_SQLMULTI:
                    for s in sql[1]:
                        self.cmdInsert(s[0], s[1])
                self.ctx.releaseDBLock()
                time.sleep(0.250)
            self.ctx.threadMonitor[self.__class__.__name__] = now
            self.ctx.checkThreads(now)
        del self.ctx.threadMonitor[self.__class__.__name__]
        self.log.info("[SQL] Terminating SQL Processor")

    def addSQL(self, sql):
        self.sqlQueue.append(sql)
        self.event.set()

    def doTerminate(self):
        self.terminate = True
        self.event.set()

    def cmdPushSensorLong(self):
        now = datetime.now()
        conn = self.ctx.openDatabase()
        cursor = conn.cursor()
        sql = "select sensorId, atTime from PushSensorShort where atTime = (select min(atTime) from PushSensorShort)"
        cursor.execute(sql)
        row = cursor.fetchone()
        if row is not None and len(row)==2:
            #self.log.debug("Sensor %s %s" % (row[0], str(row[1])))
            sensorId = row[0]
            atTime = row[1]
            if (now-atTime).total_seconds() > (3600*36):
                factor = atTime.hour / 6
                slotLow = atTime.replace(hour=factor * 6, minute=0)
                slotHigh = slotLow + timedelta(minutes=360)
                sql = "select avg(value1), min(value1), max(value1) from PushSensorShort where atTime >= ? and atTime < ? and sensorId = ?"
                cursor.execute(sql, [slotLow, slotHigh, sensorId])
                row = cursor.fetchone()
                if row is not None and len(row) == 3:
                    avgValue = row[0]
                    minValue = row[1]
                    maxValue = row[2]
                    sql = "insert into SensorLong(sensorId, avgValue, minValue, maxValue, day, sixHour) values (?,?,?,?,?,?)"
                    colValues = [sensorId, avgValue, minValue, maxValue, slotLow.timetuple().tm_yday, factor]
                    cursor.execute(sql, colValues)
                sql = "delete from PushSensorShort where atTime >= ? and atTime < ? and sensorId = ?"
                cursor.execute(sql, [slotLow, slotHigh, sensorId])
                self.addSQL([SQLProcessor.CMD_PUSHSENSORLONG])
        conn.commit()
        cursor.close()
        self.ctx.closeDatabase(conn)

    def cmdInsert(self, sql, colValues):
        conn = self.ctx.openDatabase()
        cursor = conn.cursor()
        cursor.execute(sql, colValues)
        conn.commit()
        cursor.close()
        self.ctx.closeDatabase(conn)
