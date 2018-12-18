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
                "suffix": ['String', '/set']
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
        handled = False
        for k in self.ctx.zigbee.keys():
            o = self.ctx.zigbee[k]
            if o.topic == msg.topic and not(msg.topic.endswith(self.suffix)):
                dct = json.loads(msg.payload)
                if 'state' in dct:
                    self.ctx.sdh.process(o, dct['state'].lower())
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

    def publish(self, address, message):
        self.subscriber.client.publish(address, message)

