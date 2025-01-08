import logging

from .connection import Connection

logger = logging.getLogger("AutomationOne")


class SimpleConnection(Connection):
    def __init__(self, handler, config):
        super().__init__(handler, config)
        self.factor = config.get("factor", 1)
        self.offset = config.get("offset", 0)
        self.dictionary = config.get("as_dictionary", False)

    def transform_value(self, value):
        try:
            return value * self.factor + self.offset
        except:
            return value

    def execute(self):
        super().execute()
        try:
            if isinstance(self.inNode, list):
                if self.dictionary:
                    value = {
                        node.name: self.transform_value(node.getValue())
                        for node in self.inNode
                    }
                else:
                    value = [
                        self.transform_value(node.getValue()) for node in self.inNode
                    ]
            else:
                value = self.transform_value(self.inNode.getValue())
            self.outNode.setValue(value)
        except Exception as inst:
            logger.exception(
                "Error during execution of Connection {}.".format({self.name})
            )
            if isinstance(self.inNode, list):
                logger.debug(
                    "Connection Values: {}".format(
                        [node.getValue() for node in self.inNode]
                    )
                )
            else:
                logger.debug("Connection Value: {}".format(self.inNode.getValue()))
            logger.debug(inst)
