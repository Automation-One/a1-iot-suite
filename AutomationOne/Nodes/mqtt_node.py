import logging

from .node import Node

logger = logging.getLogger("AutomationOne")


class MqttNode(Node):
    def __init__(self, handler, config):
        super().__init__(handler, config)

        self.interfaceName = config.get("interface")
        self.interface = self.handler.interfaces[self.interfaceName]

        self.mqttID = config.get("mqttID", self.name)

        self.datatype = config.get("datatype", "custom")

        self.topicPub = config.get("topicPub", None)

        self.topicSub = config.get("topicSub", None)
        if self.topicSub:
            self.interface.appendSub(self.topicSub)

        self.accessType = config.get("accessType")
        self.read = not (self.accessType == "write")
        if self.accessType and self.accessType not in ["read", "write"]:
            logger.warning(
                "AccessType '{}' for MQTT Node {} not recognized. Assuming read access.".format(
                    self.accessType, self.name
                )
            )

        if self.read:
            self.interface.registerSubscriber(self.mqttID, self)

    def setValue(self, value):
        if self.read:
            if self.datatype == "auto":
                try:
                    value = int(value)
                except:
                    try:
                        value = float(value)
                    except:
                        pass
            elif self.datatype == "custom":
                pass
            else:
                logger.warning(
                    "Datatype conversion {} for MqttNode not implemented!".format(
                        self.datatype
                    )
                )

        else:
            self.interface.encoder(self.mqttID, value, self.topicPub)
        super().setValue(value)
