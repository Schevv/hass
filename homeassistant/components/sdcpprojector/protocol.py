# Defines and protocol details from here: https://www.digis.ru/upload/iblock/f5a/VPL-VW320,%20VW520_ProtocolManual.pdf

from enum import Enum, IntFlag


class Action(Enum):
    GET = 0x01
    SET = 0x00


class Command(Enum):
    SET_POWER = 0x0130
    CALIBRATION_PRESET = 0x0002
    ASPECT_RATIO = 0x0020
    INPUT = 0x0001
    GET_STATUS_ERROR = 0x0101
    GET_STATUS_POWER = 0x0102
    GET_STATUS_LAMP_TIMER = 0x0113
    GET_ROM_VERSION = 0x011D
    GET_SC_ROM_VERSION = 0x011E
    GET_NVM_DATA_VERSION = 0x0127
    CONTRAST = 0x0010
    BRIGHTNESS = 0x0011
    COLOR = 0x0012
    HUE = 0x0013
    SHARPNESS = 0x0014
    BUTTON_MENU = 0x1529
    BUTTON_RIGHT = 0x1533
    BUTTON_LEFT = 0x1534
    BUTTON_UP = 0x1535
    BUTTON_DOWN = 0x1536
    BUTTON_ENTER = 0x155A
    BUTTON_RESET = 0x157B


class PowerStatus(Enum):
    STANDBY = 0
    START_UP = 1
    START_UP_LAMP = 2
    POWER_ON = 3
    COOLING = 4
    COOLING2 = 5


class Inputs(Enum):
    VIDEO = 0
    SVIDEO = 1
    INPUTA = 2
    COMPONENT = 3
    HMDI = 4
    DVI = 5


class ErrorCode(Enum):
    INVALID_ITEM = 0x0101
    INVALID_ITEM_REQUEST = 0x0102
    INVALID_LENGTH = 0x0103
    INVALID_DATA = 0x0104
    SHORT_DATA = 0x0111
    NOT_APPLICABLE_ITEM = 0x0180
    DIFFERENT_COMMUNITY = 0x0201
    INVALID_VERSION = 0x1001
    INVALID_CATEGORY = 0x1002
    INVALID_REQUEST = 0x1003
    SHORT_HEADER = 0x1011
    SHORT_COMMUNITY = 0x1012
    SHORT_COMMAND = 0x1013
    NETWORK_TIMEOUT = 0x2001
    COMMUNICATION_TIMEOUT = 0xF001
    CHECKSUM_ERROR = 0xF010
    FRAMING_ERROR = 0xF020
    PARITY_ERROR = 0xF030
    OVERRUN_ERROR = 0xF040
    OTHER_COMM_ERROR = 0xF050
    UNKNOWN_RESPONSE = 0xF0F0
    NVRAM_READ_ERROR = 0xF110
    NVRAM_WRITE_ERROR = 0xF120


class ErrorStatus(IntFlag):
    NO_ERROR = 0
    LAMP_ERROR = 1
    FAN_ERROR = 2
    COVER_ERROR = 4
    TEMP_ERROR = 8
    D5V_POWER_ERROR = 16
    POWER_ERROR = 32
    TEMP_WARNING = 64
    NVM_DATA_ERROR = 128

    def __str__(self) -> str:
        if self.value == 0:
            return ErrorStatus.NO_ERROR.name
        return ", ".join(x.name for x in ErrorStatus if self.value & x != 0)
