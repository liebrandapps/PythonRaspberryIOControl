import picamera
from io import BytesIO
from time import sleep




class CamModule():



    def __init__(self, resX, resY):
        self.resX = resX
        self.resY = resY

    def capture(self):
        stream = BytesIO()
        camera = picamera.PiCamera()
        camera.resolution=(self.resX, self.resY)
        camera.start_preview()
        sleep(2)
        camera.capture(stream, 'jpg')
        stream.close()
        return { 'Content-Type' : 'image/jpg', 'Content' : stream.getvalue() }

    def getSnapshot(self):
        stream = BytesIO()
        camera = picamera.PiCamera()
        camera.resolution = (self.resX, self.resY)
        camera.start_preview()
        sleep(2)
        camera.capture(stream, 'jpg')
        stream.close()
        return [ 200, stream.getvalue()]

    def saveSnapshot(self, filetoSave):
        stream = BytesIO()
        camera = picamera.PiCamera()
        camera.resolution = (self.resX, self.resY)
        camera.start_preview()
        sleep(2)
        camera.capture(stream, 'jpg')
        stream.close()
        with open(filetoSave, "wb") as f:
            f.write(stream.getvalue())