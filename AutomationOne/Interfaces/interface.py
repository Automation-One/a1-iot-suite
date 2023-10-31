import logging

logger = logging.getLogger("AutomationOne")

class Interface:
    def __init__(self,handler,config = None):
        if config is None:
            config = {}
        self.name = config.get("name")
        self.handler = handler
        self.config = config
        logger.debug(f"['{self.name}'] Creating a new Interface...")

    def start(self):
        pass

    def stop(self):
        pass

    def _init_timeloop(self,timeloop):
        pass
