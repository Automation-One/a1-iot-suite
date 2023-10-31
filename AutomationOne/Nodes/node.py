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
        self.result_of = []
        self.no_onchange_forward = False

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

    def setValue(self,value,no_onchange_forward=None):
        if no_onchange_forward is None:
            no_onchange_forward = self.no_onchange_forward
        logger.debug(f"[{self.name}] Set to '{value}'.")
        self.value = value

        try:
            if not self.lastValue and not self.lastValue == 0:
                self.lastValue = self.value
                self.onChange(no_onchange_forward = no_onchange_forward)
            elif abs(self.value-self.lastValue)>self.sensitivity-eps:
                self.lastValue = self.value
                self.onChange(no_onchange_forward = no_onchange_forward)
        except:
            if self.sensitivity <= 0 or self.lastValue != self.value:
                self.lastValue = self.value
                self.onChange(no_onchange_forward = no_onchange_forward)

    def onChange(self,no_onchange_forward = False):
        logger.debug(f"[{self.name}] Triggered onChange")
        self.onChangeCallback(self)
        if no_onchange_forward:
            logger.debug(f"[{self.name}] onchange forward blocked")
            return
        for connection in self.onChangeConnections:
            connection.execute()

    def onDemandUpdate(self):
        return False # Return False if onDemandUpdate does nothing

    def demandUpdate(self,updated):
        if self in updated:
            return
        logger.debug(f"[{self.name}] update demanded...")
        updated.append(self)
        if self.onDemandUpdate():
            return
        if not self.result_of:
            return
        if len(self.result_of) > 1:
            logger.warning(f"[{self.name}] Demanding a value of a Node which has multiple predecessors. Ignoring Request.")
            return
        self.result_of[0].demandUpdate(updated)
        self.result_of[0].execute()

    def registerOnChange(self,connection):
        self.onChangeConnections.append(connection)

    def registerResultOf(self,connection):
        self.result_of.append(connection)

    def _init_timeloop(self,timeloop):
        pass
