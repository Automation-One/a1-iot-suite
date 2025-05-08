from datetime import timedelta

from .node import Node


class FunctionNode(Node):
    def __init__(self, handler, config):
        super().__init__(handler, config)
        self.callbackName = config.get("callback")
        self.frequency = config.get("frequency", None)
        self.callback = getattr(handler.callbackModule, self.callbackName)

    def call(self):
        self.callback(self)

    def get_timeloop_callbacks(self):
        callbacks = super().get_timeloop_callbacks()
        if self.frequency:
            callbacks.append((self.call, timedelta(seconds=self.frequency)))
        return callbacks

    def onDemandUpdate(self):
        self.no_onchange_forward = True
        self.call()
        self.no_onchange_forward = False
        return True
