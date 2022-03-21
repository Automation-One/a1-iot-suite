import logging
import time
import json
import datetime

logger = logging.getLogger("AutomationOne")

def initialize(handler):
  PUSH_ON = handler.nodes["PUSH_ON"].pullValue()
  logger.info(f"Pre-Initial PUSH_ON request resulted in {PUSH_ON}")
  time.sleep(3)
  PUSH_ON = handler.nodes["PUSH_ON"].pullValue()
  logger.info(f"Initial PUSH_ON request resulted in {PUSH_ON}")
  logger.info(f"Turning off the Lamps")
  handler.nodes["BREAK_UV1"].setValue(512)
  handler.nodes["BREAK_UV2"].setValue(512)
  time.sleep(3)
  if PUSH_ON:
    logger.info(f"Turning on the Lamps")
    handler.nodes["BREAK_UV1"].setValue(256)
    handler.nodes["BREAK_UV2"].setValue(256)

def logValue(node):
  """Callback function for manually logging a value"""
  logger.info("{}: {}".format(node.name,node.getValue()))

def LSB(val):
  return val & 0xFF

def MSB(val):
  return val.to_bytes((val.bit_length() + 7) // 8, 'big')[0]



LAMP_ON = 256
LAMP_OFF = 512
DO_NOTHING = 0
def stop_UV(values,key):
  thisUV = LSB(values[0])
  otherUV = LSB(values[1])
  PUSH_ON = LSB(values[2])

  if key == stop_UV.lock and stop_UV.remove_lock:
    logger.info(f'stop_UV: Removing Lock {stop_UV.lock}')
    stop_UV.remove_lock = False
    stop_UV.lock = None
    return DO_NOTHING

  if not PUSH_ON:
    stop_UV.turn_on_pending = {"UV1":False,"UV2":False}
    stop_UV.turn_off_pending = {"UV1":False,"UV2":False}
    stop_UV.lock = None
    stop_UV.remove_lock = False

  if stop_UV.turn_on_pending[key]:
    if not PUSH_ON:
      stop_UV.turn_off_pending[key] = True
      stop_UV.turn_on_pending[key] = False
      logger.warning(f"stop_UV: PUSH_ON is OFF. Turning lamp {key} off.")
      return LAMP_OFF
    if thisUV:
      logger.info(f"stop_UV: Lamp {key} successfully turned on.")
      stop_UV.turn_on_pending[key] = False
      return DO_NOTHING
    else:
      logger.warning(f"stop_UV: Lamp {key} failed to turn on.")
      return LAMP_ON

  if stop_UV.turn_off_pending[key]:
    if not thisUV:
      logger.info(f"stop_UV: Lamp {key} successfully turned off.")
      stop_UV.turn_off_pending[key] = False
      return DO_NOTHING
    else:
      logger.warning(f"stop_UV: Lamp {key} failed to turn off.")
      return LAMP_OFF


  if not stop_UV.lock and not otherUV and PUSH_ON:
    logger.info(f"stop_UV: Turning Lamp {key} off since the other Lamp is off")
    stop_UV.turn_off_pending[key] = True
    stop_UV.lock = key
    return LAMP_OFF

  if stop_UV.lock == key and not thisUV and otherUV and PUSH_ON:
    logger.info(f"stop_UV: Turning Lamp {key} on, preparing to remove lock {stop_UV.lock}")
    stop_UV.turn_on_pending[key] = True
    stop_UV.remove_lock = True
    return LAMP_ON

  return DO_NOTHING
stop_UV.last_known_state = {"UV1":0, "UV2":0}
stop_UV.turn_on_pending = {"UV1":False,"UV2":False}
stop_UV.turn_off_pending = {"UV1":False,"UV2":False}
stop_UV.lock = None
stop_UV.remove_lock = False





def impulse_count(values,key="default"):
  UV_ON,PUSH_ON,Counter_UV = values
  logger.debug(f"impulse count for {key}. (lock = {stop_UV.lock})")
  if PUSH_ON and not key == stop_UV.lock:
    if LSB(UV_ON)==0 and impulse_count.state.get(key,False):
      impulse_count.state[key] = False
      return Counter_UV + 1
    impulse_count.state[key] = True
  else:
    impulse_count.state[key] = False
  return Counter_UV
impulse_count.state={}


def time_measurement(values,key="default"):
  UV_ON,Timer_UV = values
  if LSB(UV_ON):
    delta_T = max(time.time()-time_measurement.time.get(key,time.time()),0)
    Timer_UV =  Timer_UV + delta_T
  time_measurement.time[key] = time.time()
  return Timer_UV
time_measurement.state = {}
time_measurement.time = {}


def web_interface(node):
  """Web interface for the 'UV Example'"""
  values = node.getValue()
  if values == web_interface.lastValues:
    return
  web_interface.lastValues = values
  on_off = "ein" if values["PUSH_ON"] else "aus"
  line1 = {"name": f"Die Lampen sind {on_off}geschaltet"}
  time1 = str(datetime.timedelta(seconds = values["Timer_UV1"])).split('.', 2)[0]
  line2 = {"name": "Betriebsstunden UV Lampe 1:","value": time1}
  time2 = str(datetime.timedelta(seconds = values["Timer_UV2"])).split('.', 2)[0]
  line3 = {"name": "Betriebsstunden UV Lampe 1:","value": time2}
  line4 = {"name": "Störung UV Lampe 1:","value": str(values["Counter_UV1"])}
  line5 = {"name": "Störung UV Lampe 2:","value": str(values["Counter_UV2"])}

  data = {"lamps":[line1,line2,line3,line4,line5]}
  filename = node.config.get("interfaceFile","/cgiserver/data.json")
  try:
    with open(filename,'w') as file:
      json.dump(data,file)
    logger.debug(f"Successfully wrote state to {filename}")
  except:
    logger.warning(f"Could not write state to {filename}")
  
  
web_interface.lastValues = None


def web_interface_return(node):
  filename = node.config.get("interfaceFile","/cgiserver/out.json")
  try:
    with open(filename,'r') as file:
      data = json.load(file)
    #with open(filename,'w') as file:
    #  json.dump({},file)
  
    if data.get("reset uv1 counter",False):
      logger.info(f"Reseting Counter_UV1")
      node.handler.nodes.get("Counter_UV1").setValue(0)
    if data.get("reset uv2 counter",False):
      logger.info(f"Reseting Counter_UV2")
      node.handler.nodes.get("Counter_UV2").setValue(0)

    if data.get("reset uv1 timer",False):
      logger.info(f"Reseting Timer_UV1")
      node.handler.nodes.get("Timer_UV1").setValue(0)
    if data.get("reset uv2 timer",False):
      logger.info(f"Reseting Timer_UV2")
      node.handler.nodes.get("Timer_UV2").setValue(0)

  except:
    #logger.warning("Error during web_interface_return")
    pass