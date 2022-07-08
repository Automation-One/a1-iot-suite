

import logging
import math
import time


logger = logging.getLogger("AutomationOne")


# Functions for config00.yaml

def sign(node):
  """Callback function for creating a sign-like signal"""
  # First we load the custom configuration for this node
  # Notice that we also give default values for these parameters.

  sine_parameters = node.config.get('sine',{})
  a = sine_parameters.get('a',1)
  b = sine_parameters.get('b',1)
  c = sine_parameters.get('c',0)

  log_value = node.config.get('log_value',False)
  
  # Now We calculate the corresponding sine-value

  res = a*math.sin(b*time.time()+c)

  # Now we log the result if log_value is set to True:
  if log_value:
    logger.info("[{}] {}".format(node.name,res))

  # Finally we update the Value of the Node.
  # Notice that we use setValue for this. This has the advantage, that it also triggers
  # a check whether the value has changed (enough) since the last time, and then trigger
  # any necessary onchange events (like connections or additional callbacks...)

  node.setValue(res)
