import logging
import json


logger = logging.getLogger("AutomationOne")


def logValue(node):
  """Callback function for manually logging a value"""
  logger.info("{}: {}".format(node.name,node.getValue()))



def jsonEncoder(interface,id,value,topicPub = None):
  """Basic JSON Payload Decoder"""
  payload = json.dumps({id:value})
  interface.publish(payload,topicPub)



def jsonParser(interface, userdata,message):
  """Basic JSON Parser"""
  payload = message.payload.decode('UTF-8')
  parsed = json.loads(payload)
  for key,value in parsed.items():
    interface.setValue(key,value)