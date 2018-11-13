import json
import urllib2


class Hue:

    def __init__(self):
        pass

    def turnOn(self, host, user, lightId):
        putData ="{\"on\":true}"
        data =self.doPut(putData, "/lights/" + lightId + "/state", host, user)
        if "success" in data:
            result = "on"
        else:
            result = "off"
        return result

    def turnOff(self, host, user, lightId):
        putData ="{\"on\":false}"
        data =self.doPut(putData, "/lights/" + lightId + "/state", host, user)
        if "success" in data:
            result = "on"
        else:
            result = "off"
        return result

    def getStatus(self, host, user, lightId):
        data =self.doGet("/lights/" + lightId, host, user)
        if data["state"]["on" ]==True:
            result = "on"
        else:
            result ="off"
        return result

    def setBrightness(self, value, host, user, lightId):
        value =min(255, max(value ,0))
        putData ="{\"bri\":" + str(value) + "}"
        data =self.doPut(putData, "/lights/" + lightId + "/state", host, user)
        if "success" in data:
            result ="ok"
        else:
            result = "fail"
        return result

    def getBrightness(self, host, user, lightId):
        data =self.doGet("/lights/" + lightId)
        return data["state"]["bri"]

    def setStaticIP(self, host, user, netmask, gateway):
        putData= "{\"ipaddress\":\"" + host + "\", \"dhcp\":false, \"netmask\": \"" + netmask + "\",\"gateway\": \"" + gateway + "\"}"
        return self.doPut(putData, "/config", host, user)

    def getConfig(self, host, user ):
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request("http://" + host + "/api/" + user + "/config")
        request.add_header("Content-Type",  "application/x-www-form-urlencoded")
        request.get_method = lambda: 'GET'
        result = opener.open(request)
        data =json.load(result)
        return data

    def createUser(self, deviceType, host, user):
        postData ="{\"devicetype\":\"" + deviceType + "\"}"
        return self.doPost("", postData, host, anonymous=True)

    def doPost(self, urlPart, postData, host, user, anonymous=False):
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        if anonymous:
            request = urllib2.Request("http://" + self.host + "/api")
        else:
            request = urllib2.Request("http://" + self.host + "/api/" + self.user + "/lights/" + self.lightId + urlPart)
        request.add_header("Content-Type",  "application/x-www-form-urlencoded")
        request.get_method = lambda: 'POST'
        result = opener.open(request, data=postData)
        data =json.load(result)
        return data

    def doGet(self, urlSuffix, host, user):
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request("http://" + self.host + "/api/" + self.user + "/lights/" + self.lightId)
        request.add_header("Content-Type",  "application/x-www-form-urlencoded")
        request.get_method = lambda: 'GET'
        result = opener.open(request).read()
        data =json.loads(result)
        return data

    def doPut(self, putData, urlSuffix):
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request("http://" + self.host + "/api/" + self.user + urlSuffix)
        request.add_header("Content-Type",  "application/x-www-form-urlencoded")
        request.get_method = lambda: 'PUT'
        result = opener.open(request, data=putData)
        data =json.load(result)
        return data
