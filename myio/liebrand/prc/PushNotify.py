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
            if prio > 1:
                payload['message']['data'][PushNotification.PRIO] = prio
            # convert substructure to string as firebase won't handle it otherwise
            #for key in payload['message']['data'].keys():
            #    if type(payload['message']['data'][key] == dict):
            #        payload['message']['data'][key] = json.dumps(payload['message']['data'][key])
            payload['message']['data'] = { 'envelope' : b64encode(json.dumps(payload['message']['data'])) }

        self.log.debug(payload)
        resp = requests.post(self.url, data=json.dumps(payload), headers=headers)

        if resp.status_code == 200:
            self.log.debug('[FCM] Message sent to Firebase for delivery, response: %s' % (resp.text,))
        else:
            self.log.error('[FCM] Unable to send message to Firebase: %s' % (resp.text,))


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