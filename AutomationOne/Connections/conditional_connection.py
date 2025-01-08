import logging

from .simple_connection import SimpleConnection

logger = logging.getLogger("AutomationOne")


class ConditionalConnection(SimpleConnection):
    def __init__(self, handler, config):
        super().__init__(handler, config)
        self.conditionNodeName = config.get("conditionNode")
        self.conditionNode = handler.nodes.get("conditionNode")

    def evalCondition(self):
        return self.conditionNode.getValue()

    def execute(self):
        if self.evalCondition():
            super().execute()
        else:
            logger.debug(
                "The conditional connection {} is not executed.".format(self.name)
            )
