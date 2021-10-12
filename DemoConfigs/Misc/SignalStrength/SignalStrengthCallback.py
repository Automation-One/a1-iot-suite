import logging
import math
import time
import json
import subprocess
import re

logger = logging.getLogger("AutomationOne")


def SineComputation(values):
  """Evaluates A*sin(omega*t+phi)"""
  Frequenz, Amplitude, Phasenverschiebung = values
  t = time.time()
  res = Amplitude * math.sin(Frequenz*t+Phasenverschiebung)
  return res

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

def jsonParserX(interface, userdata,message):
  """Extended JSON Parser to also accept basic API calls"""
  payload = message.payload.decode('UTF-8')
  isjson = True
  try:
    parsed = json.loads(payload)
  except:
    isjson = False
  if isjson:
    for key,value in parsed.items():
      interface.setValue(key,value)
  else:
    api(interface,payload)

def api(interface,payload):
  payload = payload.strip()
  if payload == "help":
    answer = api_help(interface)
  elif payload == "stop":
    answer = api_stop(interface)
  elif payload == "start":
    answer = api_start(interface)
  else:
    answer = api_command_unknown(interface)
  interface.publish(answer,interface.config.get("topicAPI"))
  
def send_AT_code(AT_code):
  """Send an AT code and return the Response"""
  response = subprocess.check_output("mmcli -m 0 --command={}".format(AT_code).split()).decode('UTF-8')

  
  pattern = re.compile("response: '(.*)'\n")
  match = pattern.search(response)
  if not match:
    logger.warning("Unexpected Answer in 'send_AT_code': {}".format(response))
    return None
  return match.group(1)


def get_GSM_Signal_Strength():
  """Get the GSM Signal Strength via AT code (AT+CSQ)"""
  answer = send_AT_code("AT+CSQ")
  if not answer:
    return None
  pattern = re.compile("\+CSQ: (\d+),(\d+)")
  match = pattern.search(answer)
  if not match:
    logger.warning("Unexpected Answer in 'get_GSM_Signal_Strength': {}".format(answer))
    return None
  strength = int(match.group(1))
  

  if strength <= 31 and strength >= 0:
    return -109+2*(strength-2)
  elif strength == 99:
    logger.warning("GSM Strength 'not known or not detectable'")
    return None
  else:
    logger.warning("Unexpected Strength in 'get_GSM_Signal_Strength': {}".format(answer))
    return None

def SignalStrength(node):
  """Wrapper around get_GSM_Signal_Strength to make it a function Node"""
  value = get_GSM_Signal_Strength()
  if value:
    node.setValue(value)

#******** API *******

def api_help(interface): 
  answer = """Hilfetext für die MQTT-Schnittstelle der A1-Demo-Suite:
Das Programm unterscheidet zwischen den Folgenden zwei Eingabeformen:
- Plain Text Payloads werden als API-Aufruf Interpretiert. Die folgenden Aufrufe sind hierbei möglich:
    * help
    * start
    * stop
- JSON Payloads werden zum setzen von Sollwerten benutzt. Folgende Attribute können hierbei gesetzt werden:
    * Frequenz
    * Amplitude
    * Phasenverschiebung

Ein gültiger JSON Payload könnte demnach wie folgt aussehen:
{
  "Frequenz"  : 0.4,
  "Amplitude" : 2.0
}
Das Gateway Sendet 2 Verschiedene Werte nach Values:
  - "Harmonischer Oszillator" jede Sekunde
  - "GSM Signal Stärke in dBm" alle 5 Sekunden
"""
  return answer

def api_stop(interface):
  if interface.handler.stop():
    return "Applikation gestoppt."
  return "Applikation konnte nicht gestoppt werden."

def api_start(interface):
  try:
    if interface.handler.start():
      return "Applikation gestartet."
    return "Applikation konnte nicht gestartet werden."
  except:
    logger.exception("api_start")
  


def api_command_unknown(interface):
  return "Befehl wurde nicht erkannt."