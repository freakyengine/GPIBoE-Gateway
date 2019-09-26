#!/usr/bin/python3

# last modified 2019/09

## DOC -------------------------------------------------------------------------
# This class generates a GPIB interface based on the IEEE 488.1 specifications.
# RESTRICTION: works only as single controller and must be either listener or
# talker.
# It works with a Raspberry Pi over SPI and a two MCP23S17 port expander.
# The read/write/trigger methods return a number as success/error indicator and
# an optional data or error string as list.


import spidev
import time
import signal


class GPIB:
    # -- SPI configurations:

    # # for RaspberryPi Model B
    # SPI_MODULE = 0
    # SPI_CS = 0

    # for OrangePi Zero
    SPI_MODULE = 1
    SPI_CS = 0

    # -- class-global debug flag
    DEBUG = 0

    ## constructor / init
    def __init__(self):
        self.__DebugPrint('starting construction')

        self.__SPICreate()
        self.__ControllerInit()
        self.__LEDsInit()
        self._PE(1)

        self.__DebugPrint('finished construction')

    ## #### METHODS ------------------------------------------------------------

    # GPIB bus clear/init
    def Init(self):
        self._LED_ACT(1)  # activity LED on

        self._setIFC(1)
        time.sleep(200e-6)
        self._setIFC(0)

        self._LED_ACT(0)  # activity LED off
        return 0

    # GPIB change REN line state
    def Remote(self, state):
        self._LED_ACT(1)  # activity LED on

        self._setREN(state)

        self._LED_ACT(0)  # activity LED off
        return 0

    # GPIB write data to device with address
    def Write(self, address, data):
        if not (self._ValidateGPIBAddress(address)):
            return [-2, 'invalid GPIB address']

        if not (isinstance(data, str) and len(data) >= 0):
            return [-3, 'invalid or empty data to write']

        self.__DebugPrint('write to: ' + str(address) + '; data: ' + str(data))
        self._LED_ACT(1)  # activity LED on

        self._Talk(1)
        self._setATN(1)
        self._GPIBWriteByte(0x5F)
        self._GPIBWriteByte(0x3F)
        self._GPIBWriteByte(address + 0x20)
        self._setATN(0)

        for char in data[:-1]:
            self._GPIBWriteByte(ord(char))

        self._setEOI(1)
        self._GPIBWriteByte(ord(data[-1]))
        self._setEOI(0)

        self._LED_ACT(0)  # activity LED off
        return [0, '']

    # GPIB read data from addressed device
    def Read(self, address):
        if not (self._ValidateGPIBAddress(address)):
            return [-2, 'invalid GPIB address']

        self.__DebugPrint('read from: ' + str(address))
        self._LED_ACT(1)  # activity LED on

        self._Talk(1)
        self._setATN(1)
        self._GPIBWriteByte(0x5F)
        self._GPIBWriteByte(0x3F)
        self._GPIBWriteByte(address + 0x40)
        self._setATN(0)
        self._Talk(0)

        try:

            read_data = ''
            while (True):
                data, eoi_state = self._GPIBReadByte()
                read_data += chr(data)
                if ((read_data[-1] == '\n') or (eoi_state == 1)):  # terminate read on \n or EOI
                    self._LED_ACT(0)  # activity LED off
                    self.__DebugPrint('read complete ' + str(read_data))
                    return [0, read_data]

        except Exception as err:
            return [-4, ('GPIB read error: ' + str(err.args[0]))]

    # GPIB send trigger command to addressed device
    def Trigger(self, address):
        if not (self._ValidateGPIBAddress(address)):
            return [-2, 'invalid GPIB address']

        self.__DebugPrint('triggering: ' + str(address))
        self._LED_ACT(1)  # activity LED on

        self._Talk(1)
        self._setATN(1)
        self._GPIBWriteByte(0x5F)
        self._GPIBWriteByte(0x3F)
        self._GPIBWriteByte(address + 0x20)
        self._GPIBWriteByte(0x08)  # trigger command
        self._setATN(0)
        self._Talk(0)

        self._LED_ACT(0)  # activity LED off
        return [0, '']

    ## #### GPIB helper functions --------------------------------------------
    # validate GPIB address
    def _ValidateGPIBAddress(self, address):
        if ((address >= 1) and (address <= 30)):
            return 1
        else:
            return 0

    ## #### data handling functions --------------------------------------------
    # GPIB read timeout handler
    def __GPIBTimeoutHandler(self, signum, frame):
        self.__DebugPrint('TimeoutHandler SigNum: ' + str(signum))
        self.__DebugPrint('TimeoutHandler SigNum: ' + str(frame))
        raise Exception('Timeout occured!')

    # GPIB read data byte with handshake
    def _GPIBReadByte(self):
        self._setNDAC(1)
        self._setNRFD(0)

        # initalize signal subsystem and set alarm to 1 sec
        signal.signal(signal.SIGALRM, self.__GPIBTimeoutHandler)
        signal.alarm(1)

        while (self._getDAV() == 0):
            self.__DebugPrint('waiting for DAV')
        self._setNRFD(1)
        data = self._getDATA()
        eoi_state = self._getEOI()
        self._setNDAC(0)
        while (self._getDAV() == 1):
            self.__DebugPrint('waiting for not-DAV')
        self._setNDAC(1)

        # stop timer
        signal.alarm(0)

        self.__DebugPrint('read: ' + chr(data) + '; EOI=' + str(eoi_state))
        return data, eoi_state

    # GPIB write data byte with handshake
    def _GPIBWriteByte(self, data):
        while (self._getNRFD() == 1):
            self.__DebugPrint('waiting for NFRD')
        self._setDATA(data)
        self._setDAV(1)
        while (self._getNDAC() == 1):
            self.__DebugPrint('waiting for NDAC')
        self._setDAV(0)

        return 0

    ## #### interface functions ------------------------------------------------
    # when calling this functions logic 1 equals to 1 (standard logic)

    # Take control!
    def __ControllerInit(self):
        # data = 0x00, output
        self.__SPIDataByteWrite(0x14, 0xFF)
        self.__SPIDataByteWrite(0x00, 0x00)

        # REN=1, IFC=0, NDAC=0, NRFD=0, DAV=0, EOI=1, ATN=1, SRQ=1
        self.__SPIDataByteWrite(0x15, 0b10001111)
        # REN=out, IFC=out, NDAC=in, NRFD=in, DAV=out, EOI=out, ATN=out, SRQ=in
        self.__SPIDataByteWrite(0x01, 0b00110001)

        # TE=1, SC=1, PE=0, DC=0; all outputs
        self.__SPICtrlByteWrite(0x14, 0b11000000)
        self.__SPICtrlByteWrite(0x00, 0x00)

        # release IFC after 100µs
        time.sleep(100e-6)
        self.__SPIDataBitWrite(0x15, 6, 1)

        self.__DebugPrint('finished GPIB SC init')

    ## GPIB driver control functions -------------------------------------------

    # GPIB talk enable
    def _Talk(self, enable):
        if (enable):
            # data not valid & DAV as output
            self.__SPIDataBitWrite(0x15, 3, 1)
            self.__SPIDataBitWrite(0x01, 3, 0)
            # NRFD&NDAC as inputs
            self.__SPIDataBitWrite(0x01, 4, 1)
            self.__SPIDataBitWrite(0x01, 5, 1)
            # set TE
            self.__SPICtrlBitWrite(0x14, 7, 1)
            # data as output
            self.__SPIDataByteWrite(0x00, 0x00)
            self._LED_TALK(1)
        else:
            # DAV as input
            self.__SPIDataBitWrite(0x01, 3, 1)
            # not ready for data, not accepted & NRFD,NDAC as outputs
            self.__SPIDataBitWrite(0x15, 4, 0)
            self.__SPIDataBitWrite(0x15, 5, 0)
            self.__SPIDataBitWrite(0x01, 4, 0)
            self.__SPIDataBitWrite(0x01, 5, 0)
            # clear TE
            self.__SPICtrlBitWrite(0x14, 7, 0)
            # data as input
            self.__SPIDataByteWrite(0x00, 0xFF)
            self._LED_TALK(0)

    ## GPIB data transfer & line functions -------------------------------------
    def _getDATA(self):
        return self.__SPIDataByteRead(0x12)

    def _setDATA(self, data):
        self.__SPIDataByteWrite(0x14, ~data)

    def _PE(self, enable):  # GPIB data lines pullup control
        self.__SPICtrlBitWrite(0x14, 5, enable)

    ## GPIB control line functions ---------------------------------------------
    def _getSRQ(self):
        return not self.__SPIDataBitRead(0x13, 0)

    def _setATN(self, state):
        self._LED_ATN(state)
        self.__SPIDataBitWrite(0x15, 1, not state)

    def _getEOI(self):
        return not self.__SPIDataBitRead(0x13, 2)

    def _setEOI(self, state):
        self.__SPIDataBitWrite(0x15, 2, not state)

    def _setIFC(self, state):
        self.__SPIDataBitWrite(0x15, 6, not state)

    def _setREN(self, state):
        self.__SPIDataBitWrite(0x15, 7, not state)

    ## GPIB data handshake functions -------------------------------------------
    def _getDAV(self):
        return not self.__SPIDataBitRead(0x13, 3)

    def _setDAV(self, state):
        self.__SPIDataBitWrite(0x15, 3, not state)

    def _getNRFD(self):
        return not self.__SPIDataBitRead(0x13, 4)

    def _setNRFD(self, state):
        self.__SPIDataBitWrite(0x15, 4, not state)

    def _getNDAC(self):
        return not self.__SPIDataBitRead(0x13, 5)

    def _setNDAC(self, state):
        self.__SPIDataBitWrite(0x15, 5, not state)

    ## #### LED functions ------------------------------------------------------

    def __LEDsInit(self):
        self.__SPICtrlByteWrite(0x01, 0x00)  # LEDs are outputs

        # flash all LEDs once
        self.__SPICtrlByteWrite(0x15, 0x00)
        time.sleep(10e-3)
        self.__SPICtrlByteWrite(0x15, 0xFF)

    # LED 1
    def _LED_ACT(self, state):
        self.__SPICtrlBitWrite(0x15, 0, not state)

    # LED 2
    def _LED_TALK(self, state):
        self.__SPICtrlBitWrite(0x15, 1, not state)

    # LED 3
    def _LED_ATN(self, state):
        self.__SPICtrlBitWrite(0x15, 2, not state)

    # LED 4
    def __LED_ERR(self, state):
        self.__SPICtrlBitWrite(0x15, 3, not state)

    ## SPI bit & byte manipulation methods -------------------------------------

    # create SPI and return handle
    def __SPICreate(self):
        self.__spi = spidev.SpiDev()

        self.__spi.open(self.SPI_MODULE, self.SPI_CS)

        self.__spi.max_speed_hz = 10000000

        self.__spi.xfer([0x40, 0x0A, 0x08, 0x08])  # enable hardware address decoder

        self.__DebugPrint('finished SPI creation')

    # set bit in control registers, MCP23S17 for control has address 0x42
    def __SPICtrlBitWrite(self, register, bit, value):
        if (bit < 8):
            buf = self.__spi.xfer([0x43, register, 0x00])
            buf = buf[2]

            if (value):
                buf = buf | (1 << bit)
            else:
                buf = buf & ~(1 << bit)

            self.__spi.xfer([0x42, register, buf])
            return 0
        else:
            return -1

    # set byte in control register, MCP23S17 for control has address 0x42
    def __SPICtrlByteWrite(self, register, value):
        if (value < 256):
            self.__spi.xfer([0x42, register, value])
            return 0
        else:
            return -1

    # set bit in data registers, MCP23S17 for data has address 0x40
    def __SPIDataBitWrite(self, register, bit, value):
        if (bit < 8):
            buf = self.__spi.xfer([0x41, register, 0x00])
            buf = buf[2]

            if (value):
                buf = buf | (1 << bit)
            else:
                buf = buf & ~(1 << bit)

            self.__spi.xfer([0x40, register, buf])
        else:
            return -1

    # set byte in data register, MCP23S17 for data has address 0x40
    def __SPIDataByteWrite(self, register, value):
        if (value < 256):
            self.__spi.xfer([0x40, register, value])
            return 0
        else:
            return -1

    # read bit in data register, MCP23S17 for data has address 0x40
    def __SPIDataBitRead(self, register, bit):
        if (bit < 8):
            buf = self.__spi.xfer([0x41, register, 0x00])
            return ((buf[2] >> bit) & 1)
        else:
            return -1

    # read byte in data register, MCP23S17 for data has address 0x40
    def __SPIDataByteRead(self, register):
        tmp = self.__spi.xfer([0x41, register, 0x00])
        return (~tmp[2]) & 0xFF

    ## #### DEBUG functions ----------------------------------------------------
    def __DebugPrint(self, text_buffer):
        if (self.DEBUG):
            print(f"[DEBUG] GPIB:  {text_buffer!r}")
