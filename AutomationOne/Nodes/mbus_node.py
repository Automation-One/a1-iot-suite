import logging
import xmltodict

from datetime import timedelta

from .node import Node

logger = logging.getLogger("AutomationOne")


def getPathFromDir(dir, path, nodeName="<not given>"):
    keys = str(path).split("/")
    try:
        for key in keys:
            if isinstance(dir, list):
                key = int(key)
            dir = dir[key]
        return dir
    except:
        logger.error(f"Could not find path {path} in answer dict for node '{nodeName}'")
    return None


class MBusNode(Node):
    def __init__(self, handler, config):
        super().__init__(handler, config)
        self.interfaceName = config.get("interface")
        self.interface = self.handler.interfaces[self.interfaceName]
        self.unit = config.get("unit")

        self.doOnStartup = config.get("doOnStartup", True)

        self.pollRate = config.get("pollRate", None)

        self.fields = config.get("fields", None)

    def start(self):
        if self.doOnStartup:
            self.pullValue()

    def pullValue(self, no_onchange_forward=False):
        data = self.interface.read(self.unit)
        if not self.fields and data is not None:
            return data
        try:
            data_dict = xmltodict.parse(data)["MBusData"]
        except:
            logger.error(f"Could not parse data from MBus node {self.name}")
            return self.value

        if isinstance(self.fields, list):
            value = [getPathFromDir(data_dict, path, self.name) for path in self.fields]
        elif isinstance(self.fields, dict):
            value = {
                key: getPathFromDir(data_dict, path, self.name)
                for (key, path) in self.fields.items()
            }
        else:
            value = getPathFromDir(data_dict, self.fields, self.name)
        self.setValue(value, no_onchange_forward=no_onchange_forward)
        return value

    def _init_timeloop(self, timeloop):
        super()._init_timeloop(timeloop)
        if self.pollRate:
            timeloop._add_job(self.pullValue, timedelta(seconds=self.pollRate))
            logger.debug("Added {} to Timeloop.".format(self.name))

    def pushValue(self):
        logger.warning("Push not implemented for MBus.")

    def onDemandUpdate(self):
        if self.read:
            self.pullValue(no_onchange_forward=True)
            logger.debug(f"[{self.name}] MBus value pulled due to demand.")
            return True
        return False  # Nothing done
