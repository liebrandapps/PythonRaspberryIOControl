import requests


class IPCamera:

    def __init__(self):
        pass



    def saveSnapshot(self, url, filetoSave):
        r=requests.get(url)
        if r.status_code == 200:
            with open(filetoSave, "wb") as f:
                f.write(r.content)

    def getSnapshot(self, url):
        r=requests.get(url)
        pic = None
        if r.status_code == 200:
            pic = r.content
        return [r.status_code, pic]

