import json

import paho.mqtt.client as mqtt


class MQTTSubscriber():


    def __init__(self, ctx):
        cfgDict = {
            "mqtt" : {
                "enable": ["Boolean", False],
                "host": ["String", ""],
                "port": ["Integer", 1883],
                "keepAlive": ["Integer", 60],
                "publishTopic": ["String", "zigbee"],
                "subscribeTopic": ["String", "#"],
                "logUnknownDevices": ['Boolean', True],
                "suffix": ['String', '/set'],
                "publish": ['Boolean', False]
            }
        }
        ctx.cfg.addScope(cfgDict)
        self.ctx = ctx
        self.log = ctx.log
        self.enabled = ctx.cfg.mqtt_enable
        self.client = None
        self.host = ctx.cfg.mqtt_host
        self.port = ctx.cfg.mqtt_port
        self.keepAlive = ctx.cfg.mqtt_keepAlive
        self.subscribeTopic = ctx.cfg.mqtt_subscribeTopic
        self.logUnknownDevices = ctx.cfg.mqtt_logUnknownDevices
        self.suffix = ctx.cfg.mqtt_suffix
        self.publish = ctx.cfg.mqtt_publish

    def start(self):
        if self.enabled:
            self.log.info("[MQTT] Starting MQTT Subscriber")
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.connect(self.host, self.port, self.keepAlive)
            self.client.loop_start()
        else:
            self.log.warn("[MQTT] mqtt.start() called, but mqtt is not enabled.")

    def on_connect(self, client, userdata, flags, rc):
        self.log.debug("[MQTT] Connected to %s:%d with result code %s" % (self.host, self.port, str(rc)))
        client.subscribe(self.subscribeTopic)

    def on_message(self, client, userdata, msg):
        lenSuffix = len(self.suffix)
        handled = False
        for k in self.ctx.zigbee.keys():
            o = self.ctx.zigbee[k]
            if o.topic == msg.topic and not(msg.topic.endswith(self.suffix)):
                self.log.debug(msg.payload)
                dct = json.loads(msg.payload)
                if 'state' in dct:
                    self.ctx.sdh.process(o, dct['state'].lower())
                if 'click' in dct:
                    self.ctx.sdh.process(o, 'click:' + dct['click'].lower())
                handled = True
        for k in self.ctx.switch.keys():
            o = self.ctx.switch[k]
            if o.mqttTopic is not None and o.mqttTopic == msg.topic[:len(msg.topic)-lenSuffix] and msg.topic.endswith(self.suffix):
                self.log.debug(msg.payload)
                dct = json.loads(msg.payload)
                if 'state' in dct:
                    o.switch(dct['state'].lower())
                handled = True
        for k in self.ctx.fs20.keys():
            o = self.ctx.fs20[k]
            if o.mqttTopic is not None and o.mqttTopic == msg.topic[:len(msg.topic)-lenSuffix] and msg.topic.endswith(self.suffix):
                self.log.debug(msg.payload)
                dct = json.loads(msg.payload)
                if 'state' in dct:
                    o.switch(dct['state'].lower())
                handled = True
        for k in self.ctx.netio.keys():
            o = self.ctx.netio[k]
            if o.mqttTopic is not None and o.mqttTopic == msg.topic[:len(msg.topic)-lenSuffix] and msg.topic.endswith(self.suffix):
                self.log.debug(msg.payload)
                dct = json.loads(msg.payload)
                if 'state' in dct:
                    o.switch(dct['state'].lower())
                handled = True

        if not handled:
            self.log.debug("[MQTT] OnMessage %s %s" % (msg.topic, str(msg.payload)))


    def stop(self):
        if self.client is not None:
            self.log.info("[MQTT] Stopping MQTT Subscriber")
            self.client.loop_stop()


class MQTTPublisher:

    def __init__(self, subscriber):
        self.subscriber = subscriber

    '''
        publishEvent - if true, the message is only published, if MQTT has been configured to publish events,
            otherwise only ZigBee Events will be published
    '''
    def publish(self, address, message, publishEvent=False):
        if publishEvent:
            if not self.subscriber.publish:
                return
        self.subscriber.log.debug("[MQTT] Publish %s %s" % (address, message))
        self.subscriber.client.publish(address, message)

