
from datetime import timedelta

from .node import Node

class FunctionNode(Node):
    def __init__(self, handler, config):
        super().__init__(handler,config)
        self.callbackName = config.get("callback")
        self.frequency = config.get("frequency",None)
        self.callback = getattr(handler.callbackModule, self.callbackName)

    def call(self):
        self.callback(self)

    def _init_timeloop(self, timeloop):
        super()._init_timeloop(timeloop)
        if self.frequency:
            timeloop._add_job(self.call, timedelta(seconds=self.frequency))
