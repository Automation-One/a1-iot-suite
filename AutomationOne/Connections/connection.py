import logging
import time

from datetime import timedelta

logger = logging.getLogger("AutomationOne")


class Connection:
    def __init__(self, handler, config):
        self.handler = handler
        self.name = config.get("name")

        self.frequency = config.get("frequency", False)
        self.on_change = config.get("execute_on_change", not self.frequency)
        self.delay = config.get("delay", 0)
        self.demand = config.get("demandUpdate", False)

        self.doOnStartup = config.get("doOnStartup", False)

        self.inName = config.get("in")
        if not self.inName:
            self.inName = config.get("inNode")
        self.outName = config.get("out")
        if not self.outName:
            self.outName = config.get("outNode")

        if isinstance(self.inName, list):
            self.inNode = [self.handler.nodes[name] for name in self.inName]
            if not isinstance(self.on_change, list):
                self.on_change = [self.on_change for _ in self.inName]
        else:
            self.inNode = self.handler.nodes.get(self.inName)
        if isinstance(self.outName, list):
            self.outNode = [self.handler.nodes[name] for name in self.outName]
        else:
            self.outNode = self.handler.nodes.get(self.outName)

    def start(self):
        if self.doOnStartup:
            self.execute()

    def get_timeloop_callbacks(self):
        callbacks = []
        if self.frequency:
            callbacks.append((self.execute, timedelta(seconds=float(self.frequency))))
        return callbacks

    def execute(self):
        if self.delay:
            logger.debug(
                f"Delaying execution of connection {self.name} by {self.delay} seconds"
            )
            time.sleep(self.delay)
        if self.demand:
            self.demandUpdate([])
        logger.debug("Executing connection {}".format(self.name))

    def register(self):
        if isinstance(self.inNode, list):
            for node, on_change in zip(self.inNode, self.on_change):
                if on_change:
                    node.registerOnChange(self)
        else:
            if self.on_change:
                self.inNode.registerOnChange(self)
        if isinstance(self.outNode, list):
            for node in self.outNode:
                node.registerResultOf(self)
        else:
            self.outNode.registerResultOf(self)

    def demandUpdate(self, updated):
        logger.debug(f"[{self.name}] update demanded...")
        if isinstance(self.inNode, list):
            for node in self.inNode:
                node.demandUpdate(updated)
        else:
            self.inNode.demandUpdate(updated)

    def __str__(self):
        return "{} with name {}".format(self.__class__.__name__, self.name)
