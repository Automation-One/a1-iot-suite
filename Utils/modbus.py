#! /usr/bin/python3




import logging
import argparse
import yaml

from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)


modbus_exception_list = (ModbusIOException,ExceptionResponse)



def main():
  parser = argparse.ArgumentParser("Send Modbus Requests.")
  
  parser.add_argument('--config', "-C", type = str, help = "Configuration File (yaml).")

  parser.add_argument('--method','-M',type = str, help= "Specifies the method. Can be rtu (for Serial connections) or tcp (default: rtu)")

  #TCP
  parser.add_argument('--host','-H',type=str,help="Modbus Host (for tcp)")
  parser.add_argument('--port','-p',type=int,help="Port for the tcp connection (default: 503)")

  #RTU
  parser.add_argument('--device', "-D", help="Serial device for sending the request. (Default: /dev/ttymxc2)")
  parser.add_argument('--baudrate', "-b", type = int, help = "Baudrate for the serial connection.")
  parser.add_argument('--parity', "-P",help = "Parity for the serial connection.")
  parser.add_argument('--stopbits', "-S", type=int, help="Stopbits for the serial connection. (default = 1)")
  parser.add_argument("--bytesize", "-B", type = int, help = "Bytesize for the serial connection. (default = 8)")

  #Both
  parser.add_argument('--timeout', "-T", type=float, help="Timeout for the serial connection in seconds. (default = 1)")

  
  
  parser.add_argument("--unit","-u", type = int, help = "Modbus unit (default = 1)")
  parser.add_argument("--address", "-a", type = int, help = "Modbus Address (default = 0)")
  parser.add_argument('--functionCode', "-f",type=int,help="Functioncode for the modbus request (default = 3)")
  parser.add_argument('--count',"-c",type=int, help = "Count for the Modbus Request (default = 1)")

  parser.add_argument("values", nargs ="*",type=str,help = "Value(s) for functioncode 6")

  parser.add_argument('--verbose','-v', dest='verbose',action="store_true", help = "Verbose Output Including the returned register values")

  parser.add_argument("--dataType","-F",type = str, default = "int16", help = "Data format for the read values: int, uint, float with 16, 32 or 64 bit (default = int16)")
  parser.add_argument("--wordorder",type = str, default = '<', help = "Default: <")
  parser.add_argument("--byteorder", type = str, default = '>', help = "Default: >")

  args = parser.parse_args()
  if args.verbose:
    logger.setLevel(logging.DEBUG)

  #logger.debug("Input Arguments: {}".format(args))

  if args.config:
    try:
      with open(args.config, 'r') as stream:
        config = yaml.safe_load(stream)
      logger.debug("Reading Config from file {}: {}".format(args.config,config))

      if args.method is None:
        args.method = config.get('method')
      if args.method is None:
        args.method = "rtu"
      

      if args.method == "tcp":
        if args.host is None:
          args.host = config.get('host')
        
        if args.port is None:
          args.port = config.get('port')
      
      elif args.method == "rtu":
        if args.baudrate is None:
          args.baudrate = config.get('baudrate')

        if args.parity is None:
          args.parity = config.get('parity')

        if args.device is None:
          args.device = config.get('device')
        
        if args.stopbits is None:
          args.stopbits = config.get('stopbits')

        if args.bytesize is None:
          args.bytesize = config.get("bytesize")
        
      if args.timeout is None:
        args.timeout = config.get('timeout')

      if args.unit is None:
        args.unit = config.get("unit")
      
      if args.address is None:
        args.address = config.get("address")

      if args.functionCode is None:
        args.functionCode = config.get("functionCode")
      
      if args.count is None:
        args.count = config.get("count")



    except:
      logger.exception("An error occured while reading the Config File:")
      return False

  if args.method is None:
    args.method = 'rtu'

  if args.method == 'rtu':
    if not args.baudrate:
      logger.error("The Baudrate must be specified either in the config file or using --baudrate for rtu connections")
      return False

    if not args.parity:
      logger.error("Pairity must be specified either in the config file or  using --parity for rtu connections")
      return False

    if not args.device:
      args.device = "/dev/ttymxc2"

    if not args.stopbits:
      args.stopbits = 1

    if not args.bytesize:
      args.bytesize = 8

  elif args.method == 'tcp':
    if not args.host:
      logger.error("The Host must be specified either in the config file or using --host for tcp connections")
      return False

    if not args.port:
      args.port = 503
  else:
    logger.error("Method can only be 'rtu' or 'tcp'.")
    return False 

  if not args.timeout:
    args.timeout = 1

  if not args.unit:
    args.unit = 1
  
  if not args.address:
    args.address = 0

  if not args.functionCode:
    args.functionCode = 3
  
  if not args.count:
    args.count = 1


  if args.functionCode in [6,15] and args.count != 1:
    logger.warning("For Function Codes 6 and 15, the count is induced by the number of Arguments given. => Ignoring Count")
    args.count=1

  if args.count <1:
    logger.error("Count must be a positive integer!")
    return False

  args.word_count = args.count
  try:
    bit_number = int(args.dataType[-2:])
    if bit_number == 16:
      args.count = args.word_count * 1
    elif bit_number == 32:
      args.count = args.word_count * 2
    elif bit_number == 64:
      args.count = args.word_count * 4
    else:
      print("Unsupported Bitnumber in DataType!")
      return False

  except:
    print("Error: Unsupported DataType!")
    return False
  run(args)


def run(args):
  logger.debug("Running Modbus Connect with: {}".format(args))

  if args.method == "rtu":
    client = ModbusSerialClient( method="rtu",
      baudrate=args.baudrate, port=args.device, parity=args.parity, stopbits=args.stopbits,
      bytesize=args.bytesize, timeout=args.timeout)
  elif args.method == "tcp":
    client = ModbusTcpClient(host = args.host, port=args.port, timeout=args.timeout)
  else:
    raise(f"Method '{args.method}' is not implemented!")

  if client.connect():
    logger.debug("Connection Successfull")
  else:
    logger.error("Connection Failed")
    return False
  
  if args.functionCode in [6,15]:
    builder = BinaryPayloadBuilder(byteorder=args.byteorder,wordorder=args.wordorder)
    for value in args.values:
      if args.dataType == "int16":
        builder.add_16bit_int(int(value))
      elif args.dataType == "int32":
        builder.add_32bit_int(int(value))
      elif args.dataType == "int64":
        builder.add_64bit_int(int(value))

      elif args.dataType == "uint16":
        builder.add_16bit_uint(int(value))
      elif args.dataType == "uint32":
        builder.add_32bit_uint(int(value))
      elif args.dataType == "uint64":
        builder.add_64bit_uint(int(value))

      elif args.dataType == "float32":
        builder.add_32bit_float(float(value))
      elif args.dataType == "float16":
        builder.add_16bit_float(float(value))
      elif args.dataType == "float64":
        builder.add_64bit_float(float(value))
      else:
        logger.error("Datatype is not supported.")
        return False


  if args.functionCode == 1:
    result =  client.read_coils(args.address, count=args.count,unit = args.unit)
    if isinstance(result,modbus_exception_list):
        logger.exception(result)
        return False
    if args.verbose:
      logger.info("Returned Values: {}".format(result.registers))
  
  elif args.functionCode == 3:
    result =  client.read_holding_registers(args.address, count=args.count,unit = args.unit)
    if isinstance(result,modbus_exception_list):
      logger.exception(result)
      return False
    if args.verbose:
      logger.info("Returned Values: {}".format(result.registers))
  
  elif args.functionCode == 4:
    result =  client.read_input_registers(args.address, count=args.count,unit = args.unit)
    if isinstance(result,modbus_exception_list):
        logger.exception(result)
        return False
    if args.verbose:
      logger.info("Returned Values: {}".format(result.registers))

  elif args.functionCode == 6:
    if not client.write_registers(args.address, builder.to_registers(), unit = args.unit):
      logger.error("Write Registers failed!")
  elif args.functionCode == 15:
    if not client.write_coils(args.address,builder.to_coils(),unit = args.unit):
      logger.error("Write Coils failed!")
    

  else:
    logging.error("Function Code not yet implemented!")
    return False

  if args.functionCode in [3,4]:
    decoder =  BinaryPayloadDecoder.fromRegisters(result.registers,byteorder=args.byteorder,wordorder=args.wordorder)
    values = []
    for _ in range(args.word_count):
      if args.dataType == "int16":
        value = decoder.decode_16bit_int()
      elif args.dataType == "int32":
        value = decoder.decode_32bit_int()
      elif args.dataType == "int64":
        value = decoder.decode_64bit_int()

      elif args.dataType == "uint16":
        value = decoder.decode_16bit_uint()
      elif args.dataType == "uint32":
        value = decoder.decode_32bit_uint()
      elif args.dataType == "uint64":
        value = decoder.decode_64bit_uint()

      elif args.dataType == "float32":
        value = decoder.decode_32bit_float()
      elif args.dataType == "float16":
        value = decoder.decode_16bit_float()
      elif args.dataType == "float64":
        value = decoder.decode_64bit_float()
      else:
        logger.warning("Datatype is not supported.")
        return False
      values.append(value)
    if args.word_count == 1:
      logger.info("Parsed Value: {}".format(values[0]))
    else:
      logger.info("Parsed Values: {}".format(values))

    
  

  return True
  
    





if __name__ == "__main__":
  main()

  

