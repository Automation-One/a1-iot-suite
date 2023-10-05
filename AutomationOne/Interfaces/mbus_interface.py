"""Module, which provides a Modbus Interface as part of the AutomationOne Suite"""

import logging
import time
import subprocess

from mbus.MBus import MBus

from .interface import Interface

logger = logging.getLogger("AutomationOne")


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
