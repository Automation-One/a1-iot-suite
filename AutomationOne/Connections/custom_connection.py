
import logging

from .connection import Connection

logger = logging.getLogger("AutomationOne")


class CustomConnection(Connection):
    def __init__(self,handler,config):
        super().__init__(handler,config)
        self.callbackName = config.get("callback")
        if self.callbackName:
            self.callback = getattr(handler.callbackModule,self.callbackName)
        else:
            self.callback = lambda val: val
        self.split = config.get("split",False) #Splits the value array over multiple outnodes
        self.args = config.get("args",[])
        self.skip_on_none = config.get("skip_on_none",True) #Skip outNode-Update if callback returns None
        if not isinstance(self.args,list):
            self.args = [self.args]
        self.kwargs = config.get("kwargs",{})

    def execute(self):
        super().execute()
        try:
            if isinstance(self.inNode,list):
                value = [node.getValue() for node in self.inNode]
            else:
                value = self.inNode.getValue()
            result = self.callback(value,*self.args,**self.kwargs)
            if self.skip_on_none and result is None:
                return
            if self.split:
                for (node,x) in zip(self.outNode,result):
                    node.setValue(x)
            else:
                self.outNode.setValue(result)
        except Exception:
            logger.exception("Error during execution of Connection {}.".format({self.name}))
