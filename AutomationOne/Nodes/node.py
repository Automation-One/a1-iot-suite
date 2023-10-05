import logging

logger = logging.getLogger("AutomationOne")

eps = 1e-9

class Node:
    def __init__(self,handler,config):
        self.handler = handler
        self.name = config.get("name")

        logger.debug(f"['{self.name}'] Creating a new Node...")

        self.value = config.get("default",None)
        self.lastValue = self.value

        self.onChangeConnections = []

        if "onChange" in config:
            self.onChangeCallback = getattr(handler.callbackModule,config["onChange"])
        else:
            self.onChangeCallback = lambda node: None

        self.sensitivity = config.get("sensitivity",0)

        self.config = config

    def getValue(self):
        return self.value

    def start(self):
        pass

    def setValue(self,value):
        logger.debug(f"['{self.name}'] Set to '{value}'.")
        self.value = value

        try:
            if not self.lastValue and not self.lastValue == 0:
                self.lastValue = self.value
                self.onChange()
            elif abs(self.value-self.lastValue)>self.sensitivity-eps:
                self.lastValue = self.value
                self.onChange()
        except:
            if self.sensitivity <= 0 or self.lastValue != self.value:
                self.lastValue = self.value
                self.onChange()

    def onChange(self):
        logger.debug(f"['{self.name}'] Triggered onChange")
        self.onChangeCallback(self)
        for connection in self.onChangeConnections:
            connection.execute()

    def registerOnChange(self,connection):
        self.onChangeConnections.append(connection)

    def _init_timeloop(self,timeloop):
        pass
