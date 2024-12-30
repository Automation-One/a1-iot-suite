import logging
import time

import paho.mqtt.client as mqtt
from paho.mqtt import __version__ as MQTT_VERSION

from .interface import Interface

logger = logging.getLogger("AutomationOne")

def ultralight2(interface, userdata, message):
    payload = message.payload
    array = payload.decode('UTF-8').split('|')
    keys = array[::2]
    values = array[1::2]
    if len(values) != len(keys):
        logger.warning("Syntax error in ultralight2 payload {} (odd number of sections)".format(payload))
    for i in range(len(values)):
        interface.setValue(keys[i],values[i])

def simpleEncoder(interface,id,value,topicPub = None):
    payload =  "{} value={} {}".format(id, value, int(time.time() * 1000000000))
    interface.publish(payload,topicPub)


class MqttInterface(Interface):
    def __init__(self,handler,config):
        super().__init__(handler,config)
        self.host = config.get("host")
        self.port = config.get("port",1883)

        self.clientID = config.get("clientID","")

        self.user = config.get("user")
        self.pw = config.get("pass")

        self.keepalive = config.get("keepalive",60)
        if "topicSub" in config:
            topicSub = config.get("topicSub")
            if isinstance(topicSub,list):
                self.topicSubList = topicSub
            else:
                self.topicSubList = [topicSub]
        else:
            self.topicSubList = []

        self.topicPub = config.get("topicPub","")

        self.parserName = config.get("parser",None)
        if self.parserName == "ultralight2":
            self.parser = ultralight2
        elif self.parserName:
            self.parser = getattr(handler.callbackModule,self.parserName)
        else:
            self.parser = None
            logger.info(f"MQTT Interface {self.name} has no parser given. Ignoring incoming messages...")

        self.encoderName = config.get("encoder","simple")
        if self.encoderName == "simple":
            self._encoder = simpleEncoder
        else:
            self._encoder = getattr(handler.callbackModule,self.encoderName)

        self.encoder = lambda *args, **kwargs: self._encoder(self,*args,**kwargs)
        self.dryrun = config.get("dryrun",False)
        self.transport = config.get("transport","tcp")
        self.subs = {}
        self.tls = config.get("tls")

        if tuple(map(int, MQTT_VERSION.split('.'))) < (2, 0, 0):
            self.client = mqtt.Client(client_id=self.clientID,transport=self.transport)
        else:
            self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1,client_id=self.clientID,transport=self.transport)

        if self.tls:
            self.client.tls_set(**self.tls)

        self.client.enable_logger(logger = logger)
        if self.user:
            self.client.username_pw_set(self.user,self.pw)
            if not self.tls and not self.tls is False:
                self.client.tls_set(ca_certs=None, certfile=None, keyfile=None, ciphers=None)

        self.client.on_message = lambda client, userdata, message: self.on_message(client, userdata, message)
        self.client.on_connect = lambda  client, userdata, flags, rc: self.on_connect(client, userdata, flags, rc)

        if config.get("blocking",False ):
            self.client.connect(self.host,self.port,self.keepalive)
        else:
            self.client.connect_async(self.host,self.port,self.keepalive)

    def appendSub(self,topicSub):
        self.topicSubList.append(topicSub)

    def on_message(self,client, userdata, message):
        topic = message.topic
        payload = message.payload
        logger.debug("Received MQTT message with topic {} and payload {}.".format(topic,payload))
        if self.parser:
            self.parser(self, userdata, message)

    def on_connect(self, client, userdata, flags, rc):
        if rc==0:
            logger.info("MQTT interface {} connected successfully.".format(self.name))
            for topicSub in  self.topicSubList:
                self.client.subscribe(topicSub)
                logger.info("Subscribed to {}".format(topicSub))
        elif rc == 1:
            logger.error("MQTT interface {} connection failed: unacceptable protocol version".format(self.name))
        elif rc == 2:
            logger.error("MQTT interface {} connection failed: identifier rejected".format(self.name))
        elif rc == 3:
            logger.error("MQTT interface {} connection failed: servr unavailable".format(self.name))
        elif rc == 4:
            logger.error("MQTT interface {} connection failed: bad user name or password".format(self.name))
        elif rc == 5:
            logger.error("MQTT interface {} connection failed: not authorized".format(self.name))
        else:
            logger.error("MQTT interface {} connection failed with return code {}".format(self.name,rc))

    def start(self):
        super().start()
        self.client.loop()
        if not self.client.is_connected():
            logger.warning(f"MQTT interface {self.name} did not connect successfully on first try.")
        self.client.loop_start()

    def stop(self):
        super().stop()
        self.client.loop_stop()

    def registerSubscriber(self,id,node):
        if id in self.subs:
            logger.error("The MQTT ID {} already exists for the interface {}".format(id,self.name))
            return False
        self.subs[id] = node
        return True

    def setValue(self,id,value,dryrun = False):
        if id not in self.subs:
            logger.warning("ID {} not known to Interface {}.".format(id,self.name))
            return False
        if dryrun:
            logger.debug("Dryrun on interface {} with message ID {} successfull.".format(self.name,id))
            return True
        node = self.subs.get(id)
        node.setValue(value)
        return True

    def publish(self,payload,topicPub=None):
        if not topicPub:
            topicPub = self.topicPub
        if not self.client.is_connected():
            logger.error(f"Could not Publish via Interface {self.name} to topic {topicPub} with payload {payload} due to not being connected!")
            return False
        if self.dryrun:
            logger.debug("[Dryrun] Publishing via Interface {} to topic {} with payload {}...".format(self.name, topicPub,payload))
            return True
        logger.debug("Publishing via Interface {} to topic {} with payload {}...".format(self.name, topicPub,payload))
        self.client.publish(topicPub,payload)
        return True
