
import importlib
import importlib.util
import logging
import os
import time
import yaml

from .Connections import *
from .Interfaces import *
from .Nodes import *



from pathlib import Path
from timeloop import Timeloop


logger = logging.getLogger("AutomationOne")


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
