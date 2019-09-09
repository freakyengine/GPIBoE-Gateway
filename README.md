# GPIBoE-Gateway

Raspberry Pi (or other SBC) based GPIB over Ethernet gateway

This project is a small and inexpensive GPIB to Ethernet/LAN gateway to keep measurement hardware with GPIB alive. Due to the low cost solution it has some minor downsides with should not have an impact on the typical usage. It is suitable for any general purpose ASCII based communication with GPIB devices without or with disabled `controller` functionality. Please be aware, that this project and documentation presumes at least basic knowledge in electronics and Linux.

## Features and Limitations

* Provides a fully functional GPIB communication to any GPIB device
* Only a single master bus setup is possible (hardware limitation)
* Only ASCII based communication is possible (software limitation)

## Content of the project

* schematic of the circuit used to interface GPIB with the Raspberry Pi
* Python software for the Raspberry Pi
* this documentation file

## Hardware needed to build this project

* One Raspberry Pi (or any single board computer with a Python supported SPI module and one CS line)
* Two Microchip MCP23S17
* One Texas Instruments SN75160B
* One Texas Instruments SN75162B
* One Texas Instruments TXS0108E
* One GPIB connector (Centronics)
* A selfmade PCB or breadboard PCB and soldering tools

## Hardware

The related content is in the folder *hardware*. It contains the schematic in PDF and the original KiCAD files. The first revision on the hardware had some design flaws, which are corrected in the schematic provided. However, the PCB layout has not been reworked yet.

The hardware consists of two MCP23S17 SPI based I/O expansion ICs providing the pins needed for GPIB. Ths SPI unit is the only connection to the Raspberry Pi and uses only one CS line. The GPIB bus connection is made by one SN75160B and one SN75162B GPIB bus driver. A TXS0108E bidirectional levelshifter provides the 3.3V/5V logic conversion at the SPI bus between the Raspberry Pi (3.3V) and the MCP23S17 (5V). The GPIB circuit 5V power rail is connected to the Raspberry Pi 5V rail, so only one PSU is needed. This can be connected either at the Raspberry Pi or at the GPIB circuit. Be aware of the additional GPIB power consumption of up to 1A depending on the bus length. Four additional status LEDs are drawn in the schematic. They are not needed for the functionality and can be removed to simplifiy the design. The circuit design itself is straight forward by only connecting logic pins together.
The hardware design contains several resistors to define the GPIB interface state during the booting sequence of the Raspberry Pi. Additionally, some power supply decoupling capacitors are used and should be placed next to the ICs supply pins. An optional screw terminal is used to allow the usage of an external +5V power supply.

## Software

The source code can be found in the *software* folder.

Python is used as programming language due to the good SPI module support an the easy TCPIP communication. The software is kept as small as possible. A TCPIP server is listening on port 5025 for incoming connections. Only one connection can be active at any time as GPIB also only supports single device access. As soon as the TCPIP connection is made data can be transfered to the GPIB device. This is done by just writing to and reading from the TCPIP connection using the protocol described here.
The 'GPIB' class contains everything related to the GPIB communication including the SPI and bit manipulations on the hardware.

### Protocol
The application uses a simple ascii-based text protocol and is up to now NOT suitable for binary data transfer.
Each message consists of a command character, the GPIB target address and an optional string to write and is terminated by `\n`. These are seperated by `|`. Up to now, three commands are implemented: **W**rite,**R**ead,**T**rigger.
Every message set is answered by the gateway with a status number and, if necessary, return data. The return data may be either data read from a device or an error message. The status number and return data is also seperated by `|` and terminated by `\n`.
General protocol format to write is: `<W/R/T>|<gpibAddress>|<dataToWrite>\n`
General protocol format returned is: `<status>|<optionalData>\n`


#### Examples
1. Write
Writing `*IDN?` to a device with address 4: `W|4|*IDN?`. This will return `0` on success, or an error consisting of code and message.

1. Read
Read response from a device with address 4: `R|4` This will not write any data, but will return `0|<IDNStringRead>\n` on success, or an error consisting of code and message.

1. Trigger
Trigger via GPIB bus a device with address 4: `T|4` This will send a software trigger according the GPIB specification. It will return `0` on success, or an error consisting of code and message.

### Recommended OS setup
1. Armbian 5.90 based on Debian Buster or newer
1. Complete the post installation config.
1. Install required packages `apt-get install python3-pip python3-dev python3-setuptools`
1. Install required Python libraries `pip3 install spidev`
1. Upload the software provided in this project and make it executable.
1. For an autostart place `python3 </path/to/GPIBoE_Server.py>` in `/etc/rc.local`. [Source](https://raspberrypi.stackexchange.com/questions/8734/execute-script-on-start-up), please be aware, that this solution starts the script with `root`-permissions!
1. Change SD card mount to read-only do prevent corruption on power loss

## Conclusion

Besides the limitations the project provides an example of an very cheap single board computer (e.g. RaspberryPi) addon for communicating with GPIB enabled hardware. It allows to access good, old measurement hardware with only GPIB over the network.

The prototype uses an Orange Pi Zero with 256MB RAM and without SPI flash. It runs [Armbian 5.90 Debian Buster](https://dl.armbian.com/orangepizero/archive/Armbian_5.90_Orangepizero_Debian_buster_next_4.19.57.7z) and is powered from a 5V/1.5A power supply.
The GPIB stack was tested using a Agilent 6632B power supply unit.

## Related projects

* [Instrument Remote Control Suite](https://github.com/freakyengine/ircs)


