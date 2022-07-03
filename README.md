# a1-iot-suite

## Overview
The a1-iot-suite is an easily configurable but very flexible data handler. It's main use-case is to collect, process, translates and distribute data between different Interfaces/Protocolls like M-Bus, modbus, and MQTT. It was originally intended as a companion programm for the industrial gateways offered by AutomationOne. However the core of this software is in no way limited to specific hardware or software, and can be used on any python-capable product with minimal alterations necessary. 


### Disclaimer
This SOFTWARE PRODUCT is provided by THE PROVIDER "as is" and "with all faults." THE PROVIDER makes no representations or warranties of any kind concerning the safety, suitability, lack of viruses, inaccuracies, typographical errors, or other harmful components of this SOFTWARE PRODUCT. There are inherent dangers in the use of any software, and you are solely responsible for determining whether this SOFTWARE PRODUCT is compatible with your equipment and other software installed on your equipment. You are also solely responsible for the protection of your equipment and backup of your data, and THE PROVIDER will not be liable for any damages you may suffer in connection with using, modifying, or distributing this SOFTWARE PRODUCT.



### What the a1-iot-suite is:
 - The a1-iot-suite is a data-handler, which translates and processes data between different Interfaces and Protocolls
 - The a1-iot-suite supports a growing collection of protocols for both serial and internet comunication including, but not limited to
     - modbus (rtu and tcp)
     - MQTT
     - modbus
 - The configuration for the a1-iot-suite suite is done using at most two files, which makes mass-maintanance of and mass-deployment to many industrial iot-devices easy and error-resiliant. The Files are:
     - A yaml file, in which all interfaces, nodes and connections are defined
     - An optional python file, in which custom callback functions can be defined
 - 
 
 
 
### What the a1-iot-suite is not:
 - The a1-iot-suite is NOT a graphical tool in any way. Furthermore, there are currently no plans to include a GUI in any way.
 - The a1-iot-suite, while being fast enough for most applications, was not designed to be a real-time capable program.
 

### State of the project:
The a1-suite is currently work in prograss. Therefore there are a lot of features yet to be implemented, and sadly there might be some undiscovered bugs. If you find a bug, or would like to suggest some feature you are missing feel free to open an issue, or start a new discussion. However the a1-suite is already functional and has already been successfully deployed in different iot projects.


### Contribution:
YES, PLEASE! I am gratefull to anyone, who wants to contribute to this project. A good starting point is to have a look at the open issues, or fix any bugs you noticed.
 
## Software Design

The core-design choice was to split the configuration into three main parts:
 - **Interfaces**, which represent specific protocolls and settings, which are used collectively by many datapoints. 
 - **Nodes**, which are the representation of the actual datapoints and mostly associated to a specific interface.
 - **Connections**, which connect two or more Nodes, and allow data transfere between them

### Explanation of the design-idea using a simple example

Let's assume you want to read some modbus signal from a rotary encoder and transmit this result to a flow-regulator via the same serial connection.
For this, we would first set up the modbus *interface*, which includes for example the serial-tty-device, baudrate for modbus-rtu or host and prot for modbus-tcp. Then we would use one (input)-*node* for the signal of the rotary encoder and one (output)-*node* for flow-regulator. Finally, we use a *connection* in order to enable data-flow from one node to the other. The Configuration-File for this would look something like this:
~~~
interfaces:
  - name: Modbus Interface
    type: modbus
    method: rtu
    baudrate: 115200
    device: /dev/ttymxc2
    
nodes:
  - name: rotary encoder
    type: modbus
    interface: Modbus Interface
    address: 1
    accessType: read
    pollRate: 5  # Measure this value every 5 seconds
  
  - name: flow controller
    type: modbus
    interface: Modbus Interface
    address: 2
    accessType: write
    
connections:
  - name: rotary encoder -> flow controller
    inNode: rotary encoder
    outNode: flow controller
~~~ 
A more complete version of this can be found under DemoConfigs/ModbusExample/ModbusExample.yaml

While the example above doesn't seem to be very complex at first glance, there is already a lot, you might want to individualize. Here are some of the examples you might want to do and how we would solve them using this style of configuration file:
 - "The signal from the rotary encoder is very noisy. Therefore, the flow-controller is constantly moving" => Simple! just add a sensitivity to the rotary encoder. This way, the conections are only triggered, when the value has changed by at least the given amount.
 - "I also want to see the current signal from at home via a mqtt server." => Just add an MQTT interface, an outgoing node, and a connection to that node, and you are set.
 - "The two modbus devices use different serial ports" => Just add a second Modbus Interface with a different name (identifier) and change the "interface" property of the nodes correspondingly. You don't have to do anything else
 - "The values from the rotary encoder are between 0 and 10, but the flow controller uses values between -100 and 100" => Just add a "factor" and "offset" to the connection, in order to linearly transform one into the other
 - "Ok, but I need the transformation to be non-linear" => In this case, you can just write your own python function, where you do, what ever you want, and then reference this function in the connection. (We don't have a simple, documented example for this yet. However you can have a glance at DemoConfigs/Misc/UV_Example, where we implemented a complex state-machine whith this)

And there is still a **lot** more, you can do with this system. (like for example chaining connections, connections with multiple inputs and/or outputs, virtual nodes,...)
