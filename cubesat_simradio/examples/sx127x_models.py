from enum import Enum

class SX127x_Mode(Enum):
    SLEEP = 0x00
    STDBY = 0x01
    FSTX = 0x02
    TX = 0x03
    FSRX = 0x04
    RXCONT = 0x05
    RXSINGLE = 0x06
    CAD = 0x07

class SX127x_FSK_ISR(Enum):
    MODE_READY = 1 << 15
    RX_READY = 1 << 14
    TX_READY = 1 << 13
    PLL_LOCK = 1 << 12
    RSSI = 1 << 11
    TIMEOUT = 1 << 10
    PREAMBLE_DETECT = 1 << 9
    SYNC_ADDR_MATCH = 1 << 8
    FIFO_FULL = 1 << 7
    FIFO_EMPTY = 1 << 6
    FIFO_LEVEL = 1 << 5
    FIFO_OVERRUN = 1 << 4
    PACKET_SENT = 1 << 3
    PAYLOAD_READY = 1 << 2
    CRC_OK = 1 << 1
    LOW_BAT = 1 << 0


class SX127x_Modulation(Enum):
    LORA = 0x80
    FSK = 0

class SX127x_HeaderMode(Enum):
    EXPLICIT = 0
    IMPLICIT = 1

class SX127x_PA_Pin(Enum):
    RFO = 0
    PA_BOOST = 1

class SX127x_LoRa_ISR(Enum):
    RX_TIMEOUT = 1 << 7
    RXDONE = 1 << 6
    PAYLOAD_CRC_ERROR = 1 << 5
    VALID_HEADER = 1 << 4
    TXDONE = 1 << 3
    CAD_DONE = 1 << 2
    FHSS_CHANGE_CHANNEL = 1 << 1
    CAD_DETECTED = 1 << 0


class SX127x_BW(Enum):
    BW7_8 = 0
    BW10_4 = 1 << 4
    BW15_6 = 2 << 4
    BW20_8 = 3 << 4
    BW31_25 = 4 << 4
    BW41_7 = 5 << 4
    BW62_5 = 6 << 4
    BW125 = 7 << 4
    BW250 = 8 << 4
    BW500 = 9 << 4


class SX127x_CR(Enum):
    CR5 = 1 << 1
    CR6 = 2 << 1
    CR7 = 3 << 1
    CR8 = 4 << 1


class SX127x_ReastartRxMode(Enum):
    OFF = 0
    NO_WAIT_PLL = 1
    WAIT_PLL = 2

class SX127x_DcFree(Enum):
    OFF = 0
    MANCHESTER = 1
    WHITENING = 2
