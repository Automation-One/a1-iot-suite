import logging
import time

try:
    from pymodbus.client import ModbusSerialClient, ModbusTcpClient
except:
    from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient
from pymodbus.exceptions import ModbusIOException

from .interface import Interface

logger = logging.getLogger("AutomationOne")

class ModbusInterface(Interface):
    """A Class providing an AutomationOne Interface for Modbus"""
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
