from base64 import b64encode

import requests
import json
from oauth2client.service_account import ServiceAccountCredentials


class PushNotification:

    cfgDict = { "pushNotification" :
                    { "enable" : [ "Boolean", False ],
                      "url" : [ "String", "https://fcm.googleapis.com/v1/projects/%s/messages:send" ],
                      "scopes" : [ "String", 'https://www.googleapis.com/auth/firebase.messaging'],
                      "urlSubscribe" : [ "String", "https://iid.googleapis.com/iid/v1/%s/rel/topics/%s" ],
                      "urlUnsubscribe" : [ "String", "https://iid.googleapis.com/iid/v1/%s/rel/topics/%s" ],
                      "urlGetSubscriptions" : [ "String", "https://iid.googleapis.com/iid/info/%s?details=true" ],
                      "apiKey" : [ "String", ],
                      "serviceAccountFile" : [ "String", ],
                      "projectId" : [ "String", ],
                      "senderId" : [ "String", ],
                      "publicKey" : [ "String", ]
                      }
                }
    PRIO = "priority"

    def __init__(self, ctx):
        self.ctx = ctx
        self.log = ctx.getLogger()
        cfg = ctx.getConfig()
        cfg.addScope(PushNotification.cfgDict)
        self.isFCMEnabled = cfg.pushNotification_enable
        if self.isFCMEnabled:
            self.serviceAccountFile = cfg.pushNotification_serviceAccountFile
            self.scopes = cfg.pushNotification_scopes
            self.url = cfg.pushNotification_url % cfg.pushNotification_projectId
            self.apiKey = cfg.pushNotification_apiKey
            self.urlSubscribe = cfg.pushNotification_urlSubscribe
            self.urlUnsubscribe = cfg.pushNotification_urlUnsubscribe
            self.urlGetSubscriptions = cfg.pushNotification_urlGetSubscriptions
            self.publicKey = cfg.pushNotification_publicKey
            self.senderId = cfg.pushNotification_senderId

    def isEnabled(self):
        return self.isFCMEnabled

    def get_access_token(self):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self.serviceAccountFile, self.scopes)
        access_token_info = credentials.get_access_token()
        self.log.debug(access_token_info);
        return access_token_info.access_token

    # normal messages (prio=0) are queued in a database table, while
    # prio>0 messages are being sent immediately
    # queued messages are merged and sent out with the poller updates
    #
    def pushMessage(self, payload, prio=0):
        if prio > 0:
            self.pushMessageDirect(payload, prio)
            return
        conn = self.ctx.openDatabase()
        cursor = conn.cursor()
        sql = "insert into PNQueue(payload) values (?)"
        colValues = [json.dumps(payload),]
        cursor.execute(sql, colValues)
        conn.commit()
        cursor.close()
        self.ctx.closeDatabase(conn)


    #
    # prio > 1 is forwarded to the subscriber, if the message is a data message.
    # Intention is that a notification message may be displayed
    #
    def pushMessageDirect(self, payload, prio=0):
        if not(self.isEnabled()):
            self.log.warn("[FCM] pushMessage() called with disabled notification -> no message will be sent")
        headers = {
            'Authorization': 'Bearer ' + self.get_access_token(),
            'Content-Type': 'application/json; UTF-8'
        }

        if 'data' in payload['message']:
            # fcm has a message size limit of approx. 4kb
            # the following code recursively splits messages until each message in the set
            # is of size 2700 bytes or less
            # we work with some buffer as the (split) message needs to be wrapped into message and data plus
            # a base64 encoding is needed. Base 64 encoding adds 1/3 in size (approx.)
            loadsIn = [payload['message']['data'], ]
            didSplit = True
            while didSplit:
                didSplit = False
                loadsOut = []
                for l in loadsIn:
                    if len(json.dumps(l)) > 2700:
                        i = 0
                        d = [{}, {}]
                        for k in l.keys():
                            if k in ['msgType', 'serverId', 'timeStamp']:
                               d[0][k] = l[k]
                               d[1][k] = l[k]
                            else:
                                d[i % 2][k] = l[k]
                            i = i + 1
                        loadsOut.append(d[0])
                        loadsOut.append(d[1])
                        didSplit = True
                    else:
                        loadsOut.append(l)
                loadsIn = loadsOut

            for l in loadsIn:
                ll = {'message': {'topic': payload['message']['topic'], 'data': l}}
                if prio > 1:
                    ll['message']['data'][PushNotification.PRIO] = prio
                # convert substructure to string as firebase won't handle it otherwise
                ll['message']['data'] = {'envelope': b64encode(json.dumps(ll['message']['data']))}
                jsonString = json.dumps(ll)
                self.log.debug("[FCM] Message (%d bytes): %s" % (len(jsonString), jsonString[0:60]))
                resp = requests.post(self.url, data=jsonString, headers=headers)
                if resp.status_code == 200:
                    self.log.debug(
                        '[FCM] Message sent to Firebase for delivery, response: %s' % (resp.text.replace('\n', ' '),))
                else:
                    break

        else:
            jsonString = json.dumps(payload)
            self.log.debug("[FCM] Message (%d bytes): %s" % (len(jsonString), jsonString[0:60]))
            resp = requests.post(self.url, data=jsonString, headers=headers)
            if resp.status_code == 200:
                self.log.debug('[FCM] Message sent to Firebase for delivery, response: %s' % (resp.text.replace('\n', ' '),))

        if resp.status_code == 503:
            self.log.warn('[FCM] Unable to send message as Firebase Service is currently unavailable')
        else:
            self.log.error('[FCM] Unable to send message to Firebase: %s' % (resp.text.replace('\n', ' '),))


    def buildMessage(self, topic, title, body, data):
        #self.log.debug(data)
        return {
                'message' : {
                'topic': topic,
                'notification': {
                    'title': title,
                    'body': body
                },
            }
        }

    # dictionary must have 'flat' key / value pairs, no complex structures
    def buildDataMessage(self, topic, dataDict):
        result = {}
        result['message'] = {}
        result['message']['topic'] = topic
        result['message']['data'] = dataDict
        return result

    def addNotificationtoMessage(self, message, title, body):
        message['message']['notification'] = { 'title' : title, 'body' : body }

    def subscribeToTopic(self, token, topic):
        headers = {"Authorization": "key=" + self.apiKey}
        url = self.urlSubscribe % (token, topic)
        r = requests.post(url, headers=headers)
        if r.status_code == 200:
            self.log.debug("[FCM] OK: Created subscription for topic %s for token %s" % (topic, token))
        else:
            self.log.error("[FCM] Failed to create a subscription for topic %d %s" % (r.status_code, r.text))

    def unsubscribeFromTopic(self, token, topic):
        headers = { "Authorization" : "key=" + self.apiKey }
        url = self.urlUnsubscribe % (token, topic)
        self.log.debug(url)
        self.log.debug(headers)
        r = requests.delete(url, headers=headers)
        if r.status_code == 200:
            self.log.debug("[FCM] OK: Removed subscription for token %s" % (token))
        else:
            self.log.error("[FCM] Failed to remove a subscription for topic %d %s" % (r.status_code, r.text))

    def getSubscriptions(self, token):
        headers = {"Authorization": "key=" + self.apiKey}
        url = self.urlGetSubscriptions % (token)
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            self.log.debug("[FCM] OK: Listed subscription for token %s" % (token))
        else:
            self.log.error("[FCM] Failed to create a subscription for topic %d %s" % (r.status_code, r.text))