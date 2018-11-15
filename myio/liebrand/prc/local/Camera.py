import picamera
from io import BytesIO
from time import sleep




class CamModule():



    def __init__(self, resX, resY):
        if resX == 0:
            with picamera.PiCamera() as cam:
                if cam.revision=='ov5647':
                    resX = 2592
                    resY = 1944
                else:
                    resX = 3280
                    resY = 2464
        self.resX = resX
        self.resY = resY


    def capture(self):
        stream = BytesIO()
        camera = picamera.PiCamera()
        camera.resolution=(self.resX, self.resY)
        camera.start_preview()
        sleep(2)
        camera.capture(stream, 'png')
        pic = stream.getvalue()
        stream.close()
        camera.close()
        return { 'Content-Type' : 'image/png', 'Content' : pic }

    def getSnapshot(self):
        stream = BytesIO()
        camera = picamera.PiCamera()
        camera.resolution = (self.resX, self.resY)
        camera.start_preview()
        sleep(2)
        camera.capture(stream, 'png')
        pic = stream.getvalue()
        stream.close()
        camera.close()
        return [200, pic]

    def saveSnapshot(self, filetoSave):
        stream = BytesIO()
        camera = picamera.PiCamera()
        camera.resolution = (self.resX, self.resY)
        camera.start_preview()
        sleep(2)
        camera.capture(stream, 'png')
        with open(filetoSave, "wb") as f:
            f.write(stream.getvalue())
        stream.close()
        camera.close()
