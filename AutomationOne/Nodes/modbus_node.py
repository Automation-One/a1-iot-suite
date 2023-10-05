import logging

from datetime import timedelta

from pymodbus.exceptions import ModbusIOException
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.pdu import ExceptionResponse

from .node import Node

logger = logging.getLogger("AutomationOne")

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
        if not self.read:
            return self.value

        for i in range(self.retries):
            data = self.interface.read(self.address, self._count, self.unit,self.holding)
            #logger.debug("[Node {}] received data: {}".format(self.name,data))
            try:
                if len(data.registers)>0:
                    break
            except:
                pass
            if i+1 < self.retries:
                logger.debug(f"[{self.name}] Retrying reading Value...")
        if isinstance(data, ModbusIOException) or isinstance(data,ExceptionResponse):
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
        if self.read:
            return
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
