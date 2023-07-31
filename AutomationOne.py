#! /usr/bin/python3
from pymodbus.pdu import ExceptionResponse
import yaml

from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.exceptions import ModbusIOException

import paho.mqtt.client as mqtt

import logging
import logging.handlers
import logging.config

import time
from timeloop import Timeloop
from datetime import timedelta

import sys

import os
from pathlib import Path

import subprocess

from mbus.MBus import MBus
import xmltodict

logger = logging.getLogger("AutomationOne")
logger.setLevel(logging.DEBUG)

streamHandler = logging.StreamHandler()
streamHandler.setLevel(logging.INFO)
streamFormatter = logging.Formatter('[%(levelname)s]  %(message)s')
streamHandler.setFormatter(streamFormatter)
logger.addHandler(streamHandler)







#from importlib import import_module
#sys.path.append(".")
import importlib
import importlib.util


eps = 1e-9

def initLogger(config):
  if not "version" in config:
    config["version"]=1

  formatters = config.get("formatters",{})
  if not "AutomationOne" in formatters:
    formatters["AutomationOne"] = {"format": '[%(levelname)s]  %(message)s'}
  if not "AutomationOnePlusTime" in formatters:
    formatters["AutomationOnePlusTime"]= {"format": '%(asctime)s [%(levelname)s]  %(message)s'}
  config["formatters"] = formatters

  if not "loggers" in config:
    handlers = config.get("handlers",{}).keys()
    loggerConfig = {"AutomationOne": {"handlers": handlers}}
    config["loggers"] = loggerConfig
  logging.config.dictConfig(config)

  
class Handler:
  def __init__ (self):
    self.interfaces = {}
    self.nodes = {}
    self.connections = {}

    self.timeloop = None
    

  def start(self):
    return self._start()

  def stop(self):
    return self._stop()
    
  def _initialize(self):
    if self.initCallback:
      try:
        logger.info("Calling initCallback {}".format(self.initCallbackName))
        self.initCallback(self)
      except:
        logger.exception("Exception during initCallback!")
    for interface in self.interfaces.values():
      try:
        logger.info("Calling start() for interface {}.".format(interface.name))
        interface.start()
      except:
        logger.exception("Exception during start() of interface.")
    for node in self.nodes.values():
      try:
        logger.info("Calling start() for Node {}.".format(node.name))
        node.start()
      except:
        logger.exception("Exception during start() of Node.")
    for connection in self.connections.values():
      try:
        logger.info("Calling start() for connection {}.".format(connection.name))
        connection.start()
      except:
        logger.exception("Exception during start() for connection")
    if self.initCallback2:
      try:
        logger.info("Calling initCallback2 {}".format(self.initCallback2Name))
        self.initCallback2(self)
      except:
        logger.exception("Exception during initCallback2!")
    self._start()

  def _create_timeloop(self):
    if not self.timeloop:
      self.timeloop = Timeloop()
      logging.getLogger("timeloop").setLevel(logging.CRITICAL)
      for interface in self.interfaces.values():
        interface._init_timeloop(self.timeloop)
      for node in self.nodes.values():
        node._init_timeloop(self.timeloop)
      for connection in self.connections.values():
        connection._init_timeloop(self.timeloop)
      return True
    return False
    

  def _start(self):
    if not self._create_timeloop():
      logger.warning("Timeloop is already running and cannot be started again.")
      return False
    self.timeloop.start()
    logger.info("Timeloop Started!")
    return True
  
  def _stop(self):
    if self.timeloop:
      self.timeloop.stop()
      self.timeloop = None
      logger.info("Timeloop Stopped!")
      return True
    logger.warning("Timeloop ist not running and can therefore not be stopped.")
    return False


  def _finalize(self):
    self._stop()
    if self.finalCallback:
      logger.debug("Calling finalCallback {}".format(self.finalCallbackName))
      self.finalCallback(self)
    for interface in self.interfaces.values():
      logger.debug("Calling stop() for interface {}.".format(interface.name))
      interface.stop()

  def run(self):
    try:
      self._initialize()
      while True:
        try:
          time.sleep(1)
        except KeyboardInterrupt:
          break
    except:
      logger.exception("Exception during run!")
      raise
    finally:
      self._finalize()


  def parseConfig(self,file):
    logger.info("Loading Configuration File {}".format(file))
    with open(file, 'r') as stream:
      config = yaml.safe_load(stream)
    
    if "logging" in config:
      initLogger(config.get("logging"))
    else:
      fileHandler = logging.handlers.RotatingFileHandler("AutomationOne.log",maxBytes=1e6,backupCount=1)
      fileFormatter = logging.Formatter('%(asctime)s [%(levelname)s]  %(message)s')
      fileHandler.setFormatter(fileFormatter)
      logger.addHandler(fileHandler)
    
    if "TZ" in config:
      os.environ["TZ"] = config["TZ"]
      time.tzset()
    
    if "import" in config:
      import_path = config["import"]
      if import_path[0] != "/":  
        import_path = Path(file).resolve().parent / import_path
      logger.info("Importing Callback file {}".format(import_path))

      spec = importlib.util.spec_from_file_location("Callback",import_path)
      module = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(module)
      self.callbackModule = module
    else:
      self.callbackModule = None


    logger.debug("Callback Modul: {}".format(self.callbackModule))

    self.initCallbackName = config.get("initCallback")
    self.initCallback2Name = config.get("initCallback2") #Performed after all other initializations
    self.finalCallbackName = config.get("finalCallback")

    if self.initCallbackName:
      self.initCallback = getattr(self.callbackModule,self.initCallbackName)
    else:
      self.initCallback = None

    if self.initCallback2Name:
      self.initCallback2 = getattr(self.callbackModule,self.initCallback2Name)
    else:
      self.initCallback2 = None

    if self.finalCallbackName:
      self.finalCallback = getattr(self.callbackModule,self.finalCallbackName)
    else:
      self.finalCallback = None

    logger.debug("Setting up the Interfaces...")
    if "interfaces" in config:
      logger.info("Parsing Interfaces...")
      for interfaceConfig in config["interfaces"]:
        self.parseInterface(interfaceConfig)
    
    if "nodes" in config:
      logger.info("Parsing Nodes...")
      for nodeConfig in config["nodes"]:
        self.parseNode(nodeConfig)

    if "connections" in config:
      logger.info("Parsing Connections....")
      for connectionConfig in config["connections"]:
        self.parseConnection(connectionConfig)

    
    self.config = config
    self.custom = config.get("custom",{})

  def parseInterface(self,interfaceConfig):
    interfaceType = interfaceConfig.get("type")
    try:
      if interfaceType == "Modbus":
        interface = ModbusInterface(self,interfaceConfig)
      elif interfaceType == "MQTT":
        interface = MqttInterface(self,interfaceConfig)
      elif interfaceType == "MBus":
        interface = MBusInterface(self,interfaceConfig)
      else:
        logger.error("The interface type was not recognized! (config = {})".format(interfaceConfig))
        return False
    except:
      logger.exception("The Interface could not be created! (config = {})".format(interfaceConfig))
      return False
    return self.addInterface(interface)

  def addInterface(self,interface):
    if interface.name in self.interfaces:
      logger.warning("An interface with name {} already exists! Ignoring new interface!".format(interface.name))
      return False
    else:
      self.interfaces[interface.name] = interface
      logger.debug("Added interface: {}".format(interface))
      return True

  def parseNode(self,nodeConfig):
    nodeType = nodeConfig.get("type","default")
    try:
      if nodeType == "Modbus":
        node = ModbusNode(self,nodeConfig)
      elif nodeType == "Function":
        node = FunctionNode(self,nodeConfig)
      elif nodeType == "MQTT":
        node = MqttNode(self,nodeConfig)
      elif nodeType == "MBus":
        node = MBusNode(self,nodeConfig)
      elif nodeType == "default":
        node = Node(self,nodeConfig)
      else:
        logger.error("The node type was not recognized! (config = {})".format(nodeConfig))
        return False
    except:
      logger.exception("The node could not be created! (config = {})".format(nodeConfig))
      return False
    return self.addNode(node)

  def addNode(self,node):
    if node.name in self.nodes:
      logger.warning("A node with name '{}' already exists! Ignoring new node!".format(node.name))
      return False
    else:
      self.nodes[node.name] = node
      logger.debug("Added node: {}".format(node))
      return True

  
  def parseConnection(self,connectionConfig):
    connectionType = connectionConfig.get("type","simple")
    try:
      if connectionType.lower() == "simple":
        connection = SimpleConnection(self,connectionConfig)
      elif connectionType.lower() == "conditional":
        connection = ConditionalConnection(self,connectionConfig)
      elif connectionType.lower() == "custom":
        connection = CustomConnection(self,connectionConfig)
      else:
        logger.error("The connection type was not recognized! (config = {})".format(connectionConfig))
        return False
    except:
      logger.exception("The connection could not be created! (config = {})".format(connectionConfig))
      return False
    return self.addConnection(connection)

  def addConnection(self,connection):
    if connection.name in self.connections:
      logger.warning("A connection with name '{}' already exists! Ignoring new connection!".format(connection.name))
      return False
    else:
      self.nodes[connection.name] = connection
      connection.register()
      logger.debug("Added connection: {}".format(connection))
      return True

class Interface:
  def __init__(self,handler,config = {}):
    self.name = config.get("name")
    self.handler = handler
    self.config = config
  
  def start(self):
    pass

  def stop(self):
    pass

  def _init_timeloop(self,timeloop):
    pass
  
class ModbusInterface(Interface):
  def __init__(self,handler,config = {}):
    super().__init__(handler,config)
    self._method = config.get("method","rtu").lower()

    self._timeout = float(config.get("timeout",1))

    if self._method == "rtu":
      self._baudrate = config.get("baudrate")
      self._port = config.get("port","/dev/ttymxc2")
      self._parity = config.get("parity","E")
      self._stopbits = config.get("stopbits",1)
      self._bytesize = config.get("bytesize",8)
      
      logger.debug(f"[{self.name}] Creating Modbus Serial-rtu Client with baudrate {self._baudrate}, device {self._port}, parity {self._parity}, stopbits {self._stopbits}, bytesize {self._bytesize} and timeout {self._timeout}")
      self.client_modbus = ModbusSerialClient( method="rtu",
        baudrate=self._baudrate, port=self._port, parity=self._parity, stopbits=self._stopbits,
        bytesize=self._bytesize, timeout=self._timeout)
    elif self._method == "tcp":
      self._host = config.get("host")
      self._port = config.get("port",502)
      logger.debug(f"[{self.name}] Creating Modubs TCP Client with host {self._host}, port {self._port}, timeout {self._timeout}")
      self.client_modbus = ModbusTcpClient(host=self._host,port=self._port,timeout=self._timeout)
    else:
      raise(f"[{self.name}] Modbus Interface for method '{self._method}' is not implemented!")
    
    if self.client_modbus.connect():
      logger.debug(f"[{self.name}] Successfully connected.")
    else:
      logger.error(f"[{self.name}] Failed to connect!")
      raise("Could not connect to modbus client")

    self.force_delay = config.get("force_delay",None)
    self.force_delay_per_unit = config.get("force_delay_per_unit",None)
    self.lock = 0
    self.unit_lock = {}
    self.sleep_time = config.get("sleep_time",0.01)

    self.ReadRequests = 0
    self.Failures = 0

    self._debug_enabled = config.get("debug_enabled",False)
    if self._debug_enabled:
      self.client_modbus.debug_enabled = True


  def check_lock(self,unit):
    while self.lock>time.time() or self.unit_lock.get(unit,0)>time.time():
      time.sleep(self.sleep_time)
    if self.force_delay:
      self.lock = time.time() + self.force_delay
    if self.force_delay_per_unit:
      self.unit_lock[unit] = time.time() + self.force_delay_per_unit

  def write(self, registers, address, unit = None):
    self.check_lock(unit)
    self.client_modbus.write_registers(address, registers, unit = unit)

  def read(self, address, count, unit,holding = False):
    self.check_lock(unit)
    if holding:
      result =  self.client_modbus.read_holding_registers(address = address, count = count, unit = unit)
    else:
      result = self.client_modbus.read_input_registers(address = address, count = count, unit = unit)
    self.ReadRequests+=1
    if isinstance(result,ModbusIOException):
      self.Failures+=1
    return result

def ultralight2(interface, userdata,message):
  payload = message.payload
  array = payload.decode('UTF-8').split('|')
  keys = array[::2]
  values = array[1::2]
  if len(values) != len(keys):
    logger.warning("Syntax error in ultralight2 payload {} (odd number of sections)".format(payload))
  for i in range(len(values)):
    interface.setValue(keys[i],values[i])

def simpleEncoder(interface,id,value,topicPub = None):
  payload =  "{} value={} {}".format(id, value, int(time.time() * 1000000000))
  interface.publish(payload,topicPub)

    

class MqttInterface(Interface):
  def __init__(self,handler,config):
    super().__init__(handler,config)
    self.host = config.get("host")
    self.port = config.get("port",1883)

    self.clientID = config.get("clientID","")
    
    self.user = config.get("user")
    self.pw = config.get("pass")
    
    self.keepalive = config.get("keepalive",60)
    if "topicSub" in config:
      topicSub = config.get("topicSub")
      if isinstance(topicSub,list):
        self.topicSubList = topicSub
      else:
        self.topicSubList = [topicSub]
    else:
      self.topicSubList = []

    self.topicPub = config.get("topicPub","")

    self.parserName = config.get("parser","ultralight2")
    if self.parserName == "ultralight2":
      self.parser = ultralight2
    else:
      self.parser = getattr(handler.callbackModule,self.parserName)

    self.encoderName = config.get("encoder","simple")
    if self.encoderName == "simple":
      self._encoder = simpleEncoder
    else:
      self._encoder = getattr(handler.callbackModule,self.encoderName)

    self.encoder = lambda *args, **kwargs: self._encoder(self,*args,**kwargs)

    self.dryrun = config.get("dryrun",False)

    self.transport = config.get("transport","tcp")

    self.subs = {}

    self.tls = config.get("tls")

    self.client = mqtt.Client(self.clientID,transport=self.transport)
    
    if self.tls:
      self.client.tls_set(**self.tls)
    #else:
    #  self.client.tls_set(ca_certs=None, certfile=None, keyfile=None, ciphers=None)
    

    self.client.enable_logger(logger = logger)
    if self.user:
      self.client.username_pw_set(self.user,self.pw)
      if not self.tls and not self.tls is False:
        self.client.tls_set(ca_certs=None, certfile=None, keyfile=None, ciphers=None)
        #self.client.tls_set(ca_certs=None, certfile=None, keyfile=None, ciphers=None,cert_reqs=ssl.PROTOCOL_TLSv1_2)
        #pass

    self.client.on_message = lambda client, userdata, message: self.on_message(client, userdata, message)
    self.client.on_connect = lambda  client, userdata, flags, rc: self.on_connect(client, userdata, flags, rc)

    if config.get("blocking",False ):
      self.client.connect(self.host,self.port,self.keepalive)
    else:
      self.client.connect_async(self.host,self.port,self.keepalive)

  def appendSub(self,topicSub):
    self.topicSubList.append(topicSub)

  def on_message(self,client, userdata, message):
    topic = message.topic
    payload = message.payload
    logger.debug("Received MQTT message with topic {} and payload {}.".format(topic,payload))
    self.parser(self, userdata, message)



  
  def on_connect(self, client, userdata, flags, rc):
    if rc==0:
      logger.info("MQTT interface {} connected successfully.".format(self.name))
      for topicSub in  self.topicSubList:
        self.client.subscribe(topicSub)
        logger.info("Subscribed to {}".format(topicSub))
    elif rc == 1:
      logger.error("MQTT interface {} connection failed: unacceptable protocol version".format(self.name))
    elif rc == 2:
      logger.error("MQTT interface {} connection failed: identifier rejected".format(self.name))
    elif rc == 3:
      logger.error("MQTT interface {} connection failed: servr unavailable".format(self.name))    
    elif rc == 4:
      logger.error("MQTT interface {} connection failed: bad user name or password".format(self.name))
    elif rc == 5:
      logger.error("MQTT interface {} connection failed: not authorized".format(self.name))
    else:
      logger.error("MQTT interface {} connection failed with return code {}".format(self.name,rc))
    
  def start(self):
    super().start()
    self.client.loop()
    if not self.client.is_connected():
      logger.warning(f"MQTT interface {self.name} did not connect successfully on first try.")
    self.client.loop_start()

  def stop(self):
    super().stop()
    self.client.loop_stop()

  def registerSubscriber(self,id,node):
    if id in self.subs:
      logger.error("The MQTT ID {} already exists for the interface {}".format(id,self.name))
      return False
    self.subs[id] = node
    return True

  def setValue(self,id,value,dryrun = False):
    if id not in self.subs:
      logger.warning("ID {} not known to Interface {}.".format(id,self.name))
      return False
    if dryrun:
      logger.debug("Dryrun on interface {} with message ID {} successfull.".format(self.name,id))
      return True
    node = self.subs.get(id)
    node.setValue(value)
    return True

  def publish(self,payload,topicPub=None):
    if not topicPub:
      topicPub = self.topicPub
    if self.dryrun:
      logger.debug("[Dryrun] Publishing via Interface {} to topic {} with payload {}...".format(self.name, topicPub,payload))
      return 
    logger.debug("Publishing via Interface {} to topic {} with payload {}...".format(self.name, topicPub,payload))
    self.client.publish(topicPub,payload)


class MBusInterface(Interface):
  def __init__(self,handler,config = {}):
    super().__init__(handler,config)

    self.device = config.get("device",None)
    self.host = config.get("host",None)
    self.port = config.get("port",None)
    self.use_api = config.get("use_api",True)
    self._lock = False

    if self.use_api is False:
      logger.info(f"Use of API deactivated for {self.name}. Using console calls instead.")
    else:
      if self.device:
        self.mbus = MBus(device=self.device)
      else:
        self.mbus = MBus(host=self.host,port=self.port)
      
      
      self.mbus.connect()
      logger.info(f"Successfully connected to Mbus {self.name}")

  def __del__(self):
    try:
      self.mbus.disconnect()
      logger.info(f"Successfully disconnected from Mbus {self.name}")
    except:
      logger.warning("Could not properly disconnect M-Bus!")

  def write(self, unit):
    logger.warning("M-Bus write is not yet implemented!")

  def read_api(self, unit):
    reply_data=None
    result = None
    try:
      self.mbus.send_request_frame(unit)
      reply = self.mbus.recv_frame()
      reply_data = self.mbus.frame_data_parse(reply)
      result = self.mbus.frame_data_xml(reply_data)

    except:
      logger.error(f"Error during read from M-Bus {self.name} with address {unit}")
    if reply_data:
      self.mbus.frame_data_free(reply_data)
    return result
  
  def read_console(self,unit):
    command = f"mbus-serial-request-data -b 2400 {self.device} {unit}"
    logger.debug(f"Calling Console command '{command}'.")
    result = subprocess.check_output(command.split(' '))
    return result
  
  def read(self, unit):
    while self._lock:
      time.sleep(0.05)
    self._lock=True
    if self.use_api is True:
      result = self.read_api(unit)
    elif isinstance(self.use_api, dict) and self.use_api.get(unit,True):
      result = self.read_api(unit)
    else:
      result = self.read_console(unit)
    
    self._lock=False
    return result








class Node:
  def __init__(self,handler,config):
    self.handler = handler
    self.name = config.get("name")

    self.value = config.get("default",None)
    self.lastValue = self.value

    self.onChangeConnections = []

    if "onChange" in config:
      self.onChangeCallback = getattr(handler.callbackModule,config["onChange"])
    else:
      self.onChangeCallback = lambda node: None

    self.sensitivity = config.get("sensitivity",0)

    self.config = config

  def getValue(self):
    return self.value

  def start(self):
    pass

  def setValue(self,value):
    logger.debug("Node {} set to {}.".format(self.name,value))
    self.value = value

    try:
      if not self.lastValue and not self.lastValue == 0:
        self.lastValue = self.value
        self.onChange()
      elif abs(self.value-self.lastValue)>self.sensitivity-eps:
        self.lastValue = self.value
        self.onChange()
    except:
      if self.sensitivity <= 0 or self.lastValue != self.value:
        self.lastValue = self.value
        self.onChange()
      



  def onChange(self):
    self.onChangeCallback(self)
    for connection in self.onChangeConnections:
      connection.execute()

  def registerOnChange(self,connection):
    self.onChangeConnections.append(connection)

  def _init_timeloop(self,timeloop):
    pass

class FunctionNode(Node):
  def __init__(self, handler, config):
    super().__init__(handler,config)
    self.callbackName = config.get("callback")
    self.frequency = config.get("frequency",None)
    self.callback = getattr(handler.callbackModule,self.callbackName)

    
      
  def call(self):
    self.callback(self)
  
  def _init_timeloop(self, timeloop):
    super()._init_timeloop(timeloop)
    if self.frequency:
      timeloop._add_job(self.call,timedelta(seconds=self.frequency))


class ModbusNode(Node):
  def __init__(self, handler, config):
    super().__init__(handler,config)
    self.interfaceName = config.get("interface")
    self.interface = self.handler.interfaces[self.interfaceName]
    self.unit = config.get("unit")
    self.address = config.get("address")  
    self.dataType = config.get("dataType")
    self.byteorder = config.get("byteorder")
    self.wordorder = config.get("wordorder")

    if self.dataType[-1]=='i':
      if self.wordorder is not None:
        logger.warning("Node '{}': Wordorder superseded by dataType")
      self.wordorder = '>'
      self.dataType = self.dataType[:-1]
    if not self.wordorder:
      self.wordorder = '<'
    if not self.byteorder:
      self.byteorder = '>'
    
    self.retries = config.get("retries",1)

    if self.dataType == "int16":
      self._count = 1
    elif self.dataType == "int32":
      self._count = 2
    elif self.dataType == "int64":
      self._count = 4
    elif self.dataType == "uint16":
      self._count = 1
    elif self.dataType == "uint32":
      self._count = 2
    elif self.dataType == "uint64":
      self._count = 4
    elif self.dataType == "float16":
      self._count = 1
    elif self.dataType == "float32":
      self._count = 2
    elif self.dataType == "float64":
      self._count = 4
    else:
      raise NotImplementedError(f"DataType {self.dataType} not implemented for ModbusNode.")

    self.holding = config.get("HoldingRegister",False)

    self.accessType = config.get("accessType")
    self.read = not (self.accessType=="write")
    if self.accessType and self.accessType not in ["read","write"]:
      logger.warning(f"AccessType '{self.accessType}' for Modbus Node {self.name} not recognized. Assuming read access.")

    self.doOnStartup = config.get("doOnStartup", self.read)

    self.pollRate = config.get("pollRate",None)
    logger.debug(config)
    #logger.debug("pollRate = {}".format(self.pollRate))

  def start(self):
    if self.doOnStartup:
      self.pullValue()
      self.pushValue()

  def pullValue(self):
    if self.read:
      for i in range(self.retries):
        data = self.interface.read(self.address, self._count, self.unit,self.holding)
        #logger.debug("[Node {}] received data: {}".format(self.name,data))
        try:
          if len(data.registers)>0:
            break
        except:
          pass
        if i+1 < self.retries:
          logger.info(f"Retrying Modbus connection {self.name}")
      if isinstance(data,ModbusIOException) or isinstance(data,ExceptionResponse):
        logger.error("[Node {}] {}".format(self.name,data))
        return self.value
      decoder =  BinaryPayloadDecoder.fromRegisters(data.registers,byteorder=self.byteorder,wordorder=self.wordorder)

      if self.dataType == "int16":
        value = decoder.decode_16bit_int()
      elif self.dataType == "int32":
        value = decoder.decode_32bit_int()
      elif self.dataType == "int64":
        value = decoder.decode_64bit_int()

      elif self.dataType == "uint16":
        value = decoder.decode_16bit_uint()
      elif self.dataType == "uint32":
        value = decoder.decode_32bit_uint()
      elif self.dataType == "uint64":
        value = decoder.decode_64bit_uint()

      elif self.dataType == "float32":
        value = decoder.decode_32bit_float()
      elif self.dataType == "float16":
        value = decoder.decode_16bit_float()
      elif self.dataType == "float64":
        value = decoder.decode_64bit_float()

      #logger.debug("[VALUE] {} => {}".format(self.name,value))
      self.setValue(value)
      return value

  def _init_timeloop(self, timeloop):
    super()._init_timeloop(timeloop)
    if self.read and self.pollRate:
      timeloop._add_job(self.pullValue,timedelta(seconds=self.pollRate))
      logger.debug("Added {} to Timeloop.".format(self.name))

  def pushValue(self):
    if not self.read:
      #logger.debug("pushing Value")
      builder = BinaryPayloadBuilder(byteorder=self.byteorder,wordorder=self.wordorder)
      if self.dataType == "int16":
        builder.add_16bit_int(int(self.value))
      elif self.dataType == "int32":
        builder.add_32bit_int(int(self.value))      
      elif self.dataType == "int64":
        builder.add_64bit_int(int(self.value))

      elif self.dataType == "uint16":
        builder.add_16bit_uint(int(self.value))
      elif self.dataType == "uint32":
        builder.add_32bit_uint(int(self.value))      
      elif self.dataType == "uint64":
        builder.add_64bit_uint(int(self.value))

      elif self.dataType == "float16":
        builder.add_16bit_float(float(self.value))
      elif self.dataType == "float32":
        builder.add_32bit_float(float(self.value))
      elif self.dataType == "float64":
        builder.add_64bit_float(float(self.value))
      registers = builder.to_registers()
      self.interface.write(registers, self.address, self.unit)

  def setValue(self,value):
    super().setValue(value)
    self.pushValue()

  def __str__(self):
    return "ModbusNode '{}' with interface '{}', unit {}, address {}, dataType {}".format(self.name,self.interfaceName,self.unit,self.address,self.dataType)

class MqttNode(Node):
  def __init__(self, handler, config):
    super().__init__(handler,config)

    self.interfaceName = config.get("interface")
    self.interface = self.handler.interfaces[self.interfaceName]

    self.mqttID = config.get("mqttID",self.name)

    self.datatype = config.get("datatype","custom")

    self.topicPub = config.get("topicPub",None)
    
    self.topicSub = config.get("topicSub",None)
    if self.topicSub:
      self.interface.appendSub(self.topicSub)

    self.accessType = config.get("accessType")
    self.read = not (self.accessType=="write")
    if self.accessType and self.accessType not in ["read","write"]:
      logger.warning("AccessType '{}' for MQTT Node {} not recognized. Assuming read access.".format(self.accessType,self.name))

    if self.read:
      self.interface.registerSubscriber(self.mqttID,self)

  def setValue(self,value):
    if self.read:
      if self.datatype == "auto":
        try:
          value = int(value)
        except:
          try:
            value = float(value)
          except:
            pass
      elif self.datatype == "custom":
        pass
      else:
        logger.warning("Datatype conversion {} for MqttNode not implemented!".format(self.datatype))

    else:
      self.interface.encoder(self.mqttID,value,self.topicPub)
    super().setValue(value)


def getPathFromDir(dir,path,nodeName = "<not given>"):
  keys = str(path).split('/')
  try:
    for key in keys:
      if isinstance(dir,list):
        key = int(key)
      dir = dir[key]
    return dir
  except:
    logger.error(f"Could not find path {path} in answer dict for node '{nodeName}'")
  return None



class MBusNode(Node):
  def __init__(self, handler, config):
    super().__init__(handler,config)
    self.interfaceName = config.get("interface")
    self.interface = self.handler.interfaces[self.interfaceName]
    self.unit = config.get("unit")

    self.doOnStartup = config.get("doOnStartup", True)

    self.pollRate = config.get("pollRate",None)

    self.fields = config.get("fields",None)

  def start(self):
    if self.doOnStartup:
      self.pullValue()

  def pullValue(self):
    data = self.interface.read(self.unit)
    if not self.fields and data is not None:
      return data
    try:
      data_dict = xmltodict.parse(data)["MBusData"]
    except:
      logger.error(f"Could not parse data from MBus node {self.name}")
      return self.value
    
    if isinstance(self.fields,list):
      value =  [getPathFromDir(data_dict,path,self.name) for path in self.fields]
    elif isinstance(self.fields,dict):
      value =  {key:getPathFromDir(data_dict,path,self.name) for (key,path) in self.fields.items()}
    else:
      value =  getPathFromDir(data_dict,self.fields,self.name)
    self.setValue(value)
    return value

  def _init_timeloop(self, timeloop):
    super()._init_timeloop(timeloop)
    if self.pollRate:
      timeloop._add_job(self.pullValue,timedelta(seconds=self.pollRate))
      logger.debug("Added {} to Timeloop.".format(self.name))

  def pushValue(self):
    logger.warning("Push not implemented for MBus.")

  def setValue(self,value):
    super().setValue(value)















class Connection:
  def __init__(self,handler,config):
    self.handler = handler
    self.name = config.get("name")

    
    self.frequency = config.get("frequency",False)
    self.on_change = config.get("execute_on_change", not self.frequency)
    self.delay = config.get("delay", 0)


    self.doOnStartup = config.get("doOnStartup",False)
    
    self.inName = config.get("in")
    if not self.inName:
      self.inName = config.get("inNode")
    self.outName = config.get("out")
    if not self.outName:
      self.outName = config.get("outNode")

    if isinstance(self.inName,list):
      self.inNode = [self.handler.nodes[name] for name in self.inName]
      if not isinstance(self.on_change,list):
        self.on_change = [self.on_change for _ in self.inName]
    else:
      self.inNode = self.handler.nodes.get(self.inName)
    if isinstance(self.outName,list):
      self.outNode = [self.handler.nodes[name] for name in self.outName]
    else:
      self.outNode = self.handler.nodes.get(self.outName)

  def start(self):
    if self.doOnStartup:
      self.execute()

  def _init_timeloop(self,timeloop):
    if self.frequency:
      timeloop._add_job(self.execute,timedelta(seconds=float(self.frequency))) 

  def execute(self):
    if self.delay:
      logger.debug(f"Delaying execution of connection {self.name} by {self.delay} seconds")
      time.sleep(self.delay)
    logger.debug("Executing connection {}".format(self.name))

  def register(self):
    if isinstance(self.inNode,list):
      for node,on_change in zip(self.inNode,self.on_change):
        if on_change:
          node.registerOnChange(self)
    else:
      if self.on_change:
        self.inNode.registerOnChange(self)

  def __str__(self):
    return "{} with name {}".format(self.__class__.__name__,self.name)
    

class SimpleConnection(Connection):
  def __init__(self,handler,config):
    super().__init__(handler,config)
    self.factor = config.get("factor",1)
    self.offset = config.get("offset",0)
    self.dictionary = config.get("as_dictionary",False)

  def execute(self):
    super().execute()
    try:
      if isinstance(self.inNode,list):
        if self.dictionary:
          value = {node.name:node.getValue()*self.factor+self.offset for node in self.inNode}
        else:
          value = [node.getValue()*self.factor+self.offset for node in self.inNode]
      else:
        value = self.inNode.getValue()*self.factor+self.offset
      self.outNode.setValue(value)
    except Exception as inst:
      logger.exception("Error during execution of Connection {}.".format({self.name}))
      if isinstance(self.inNode,list):
        logger.debug("Connection Values: {}".format([node.getValue() for node in self.inNode]))
      else:
        logger.debug("Connection Value: {}".format(self.inNode.getValue()))
      logger.debug(inst)

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
      if self.split:
        for (node,x) in zip(self.outNode,result):
          node.setValue(x)
      else:
        self.outNode.setValue(result)
    except Exception:
      logger.exception("Error during execution of Connection {}.".format({self.name}))
    

class ConditionalConnection(SimpleConnection):
  def __init__(self,handler,config):
    super().__init__(handler,config)
    self.conditionNodeName = config.get("conditionNode")
    self.conditionNode = handler.nodes.get("conditionNode")
  
  def evalCondition(self):
    return self.conditionNode.getValue()
  
  def execute(self):
    if self.evalCondition():
      super().execute()
    else:
      logger.debug("The conditional connection {} is not executed.".format(self.name))
    
    
def main():
  configFile = "config.yaml"
  if len(sys.argv) > 1:
    configFile = sys.argv[1]

  handler = Handler()
  handler.parseConfig(configFile)
  handler.run()
 
if __name__ == "__main__":
  main()
  






