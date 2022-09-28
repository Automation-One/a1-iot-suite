

import logging
import math
import time


logger = logging.getLogger("AutomationOne")


# Functions for config00.yaml

def sine(node):
  """Callback function for creating a sine-like signal of the form a*sin(b*t+c)"""
  # First we load the custom configuration for this node
  # Notice that we also give default values for these parameters.

  sine_parameters = node.config.get('sine',{})
  a = sine_parameters.get('a',1)
  b = sine_parameters.get('b',0.1)
  c = sine_parameters.get('c',0)
  
  # Now We calculate the corresponding sine-value

  res = a*math.sin(b*time.time()+c)

  # Finally we update the Value of the Node.
  # Notice that we use setValue for this. This has the advantage, that it also triggers
  # a check whether the value has changed (enough) since the last time, and then trigger
  # any necessary onchange events (like connections or additional callbacks...)

  node.setValue(res)
  
  
def add_Nodes(values):
  """Callback function for adding the values of multiple nodes"""
  # when multiple nodes are specified as in-nodes, values is a list/dictionary in the same order
  # as specified in the configuration. For this function, we assume, that the values were given
  # as a list for the sake of simplicity.
  #
  # It is possible to access individual values by using values[0],values[1] and so forth. In this
  # case however, care should be taken, that the array is always long enough for this.
  # 
  # In this case, we will use the inbuild sum function in order to sum up all values.
  return sum(values);


def log_value(node):
  logger.info("[{}] {}".format(node.name,node.getValue()))