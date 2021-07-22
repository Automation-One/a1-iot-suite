
import logging


logger = logging.getLogger("AutomationOne")




def logValue(node):
  """Callback function for manually logging a value"""
  logger.info("{}: {}".format(node.name,node.getValue()))