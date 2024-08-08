#! py3

import asyncio
from collections import namedtuple
import socket
from struct import *

from .protocol import *

ProjectorInfo = namedtuple(
    "ProjectorInfo",
    [
        "version",
        "category",
        "community",
        "id",
        "product_name",
        "serial_number",
        "power_state",
        "location",
        "ip",
    ],
)

DEFAULT_UDP_IP = ""
DEFAULT_UDP_PORT = 53862
DEFAULT_UDP_TIMEOUT = 31
DEFAULT_TCP_PORT = 53484
DEFAULT_TCP_TIMEOUT = 2


async def async_find_projector(
    udp_ip: str = None, udp_port: int = None, timeout: float = None
) -> list[ProjectorInfo]:
    """Tries to find projectors on the network using SDAP"""
    udp_port = udp_port if udp_port is not None else DEFAULT_UDP_PORT
    udp_ip = udp_ip if udp_ip is not None else DEFAULT_UDP_IP
    timeout = timeout if timeout is not None else DEFAULT_UDP_TIMEOUT

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)

    sock.bind((udp_ip, udp_port))

    await asyncio.sleep(timeout)

    devices = []

    cont = True

    while cont:
        try:
            sdap_buffer, addr = sock.recvfrom(1028)
            info = ProjectorInfo(
                version=int(sdap_buffer[2]),
                category=int(sdap_buffer[3]),
                community=decode_text_field(sdap_buffer[4:8]),
                id=sdap_buffer[0:2].decode(),
                product_name=decode_text_field(sdap_buffer[8:20]),
                serial_number=unpack(">I", sdap_buffer[20:24])[0],
                power_state=unpack(">H", sdap_buffer[24:26])[0],
                location=decode_text_field(sdap_buffer[26:]),
                ip=str(addr[0]),
            )
            if all(dev for dev in devices if dev.ip != info.ip):
                devices.append(info)
        except:
            cont = False
    return devices


def create_command_buffer(
    projector_info: ProjectorInfo, action: Action, command: Command, data: int = None
) -> bytearray:
    # create bytearray in the right size
    if data is not None:
        my_buf = bytearray(12)
    else:
        my_buf = bytearray(10)
    # header
    my_buf[0] = 2  # only works with version 2, don't know why
    my_buf[1] = projector_info.category
    # community
    my_buf[2] = ord(projector_info.community[0])
    my_buf[3] = ord(projector_info.community[1])
    my_buf[4] = ord(projector_info.community[2])
    my_buf[5] = ord(projector_info.community[3])
    # command
    my_buf[6] = action.value
    pack_into(">H", my_buf, 7, command.value)
    if data is not None:
        # add data len
        my_buf[9] = 2  # Data is always 2 bytes
        # add data
        pack_into(">H", my_buf, 10, data)
    else:
        my_buf[9] = 0
    return my_buf


def process_command_response(msgBuf: bytearray) -> tuple[bool, int, int]:
    # my_header = Header(
    #    version=int(msgBuf[0]),
    #    category=int(msgBuf[1]),
    #    community=decode_text_field(msgBuf[2:6]),
    # )
    is_success = bool(msgBuf[6])
    command = unpack(">H", msgBuf[7:9])[0]
    data_len = int(msgBuf[9])
    if data_len != 0:
        data = unpack(">H", msgBuf[10 : 10 + data_len])[0]
    else:
        data = None
    return is_success, command, data


def decode_text_field(buf):
    """Convert char[] string in buffer to python str object
    :param buf: bytearray with array of chars
    :return: string
    """
    return buf.decode().strip(b"\x00".decode())


class ProjectorException(Exception):
    def __init__(self, error_code: ErrorCode, *args) -> None:
        super().__init__(self, *args)
        self.error_code = error_code


class Powerstate:
    def __init__(self, state: int) -> None:
        self._state = state

    @property
    def state(self) -> int:
        return self._state

    @property
    def state_name(self) -> str:
        return PowerStatus(self._state).name

    @property
    def is_on(self) -> bool:
        return self._state == 3

    @property
    def is_off(self) -> bool:
        return self._state == 0

    @property
    def is_powering_on(self) -> bool:
        return self._state == 1 or self._state == 2

    @property
    def is_powering_off(self) -> bool:
        return self._state == 4 or self._state == 5

    def __str__(self) -> str:
        return PowerStatus(self._state).name

    def __repr__(self) -> str:
        return f"Powerstate({self._state})"


class Projector:
    """Allows control of a SDCP projector"""

    def __init__(
        self, projector_info: ProjectorInfo, port: int = None, timeout: float = None
    ) -> None:
        """Base class for projector communication.
        Enables communication with Projector, Sending commands and Querying Power State
        """
        self.info = projector_info
        self.port = port if port is not None else DEFAULT_TCP_PORT
        self.timeout = timeout if timeout is not None else DEFAULT_TCP_TIMEOUT

    def __eq__(self, other):
        return self.info.serial_number == other.info.serial_number

    def _send_command(
        self, action: Action, command: Command, data=None, timeout: float = None
    ) -> int:
        timeout = timeout if timeout is not None else self.timeout
        my_buf = create_command_buffer(self.info, action, command, data)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((self.info.ip, self.port))
            sent = sock.send(my_buf)
        except TimeoutError as exc:
            raise Exception(f"Timeout while trying to send command {command}") from exc

        if len(my_buf) != sent:
            raise ConnectionError(
                f"Failed sending entire buffer to projector. Sent {sent} out of {len(my_buf)} !"
            )
        response_buf = sock.recv(1024)
        sock.close()

        is_success, _, data = process_command_response(response_buf)

        if not is_success:
            error_code = ErrorCode(data)

            raise ProjectorException(
                error_code, f"Failure after sending command {command}: {error_code}"
            )
        return data

    def _send_set_command(self, command: int, data=None, timeout: float = None) -> int:
        return self._send_command(Action.SET, command, data, timeout)

    def _send_get_command(self, command: int, data=None, timeout: float = None) -> int:
        return self._send_command(Action.GET, command, data, timeout)

    def set_power(self, is_on: bool = True) -> None:
        powerstate = PowerStatus.START_UP if is_on else PowerStatus.STANDBY
        self._send_set_command(Command.SET_POWER, data=powerstate.value)

    def get_power(self) -> Powerstate:
        data = self._send_get_command(Command.GET_STATUS_POWER)
        return Powerstate(data)

    def get_input(self) -> Inputs:
        data = self._send_get_command(Command.INPUT)
        return Inputs(data)

    def set_input(self, value: Inputs) -> None:
        self._send_set_command(Command.INPUT, data=value.value)

    def get_error(self) -> ErrorStatus:
        data = self._send_get_command(Command.GET_STATUS_ERROR)
        return ErrorStatus(data)

    def set_contrast(self, value: int) -> None:
        self._send_set_command(Command.CONTRAST, data=value)

    def get_contrast(self) -> int:
        return self._send_get_command(Command.CONTRAST)

    def set_brightness(self, value: int) -> None:
        self._send_set_command(Command.BRIGHTNESS, data=value)

    def get_brightness(self):
        return self._send_get_command(Command.BRIGHTNESS)

    def set_color(self, value: int) -> None:
        self._send_set_command(Command.COLOR, data=value)

    def get_color(self):
        return self._send_get_command(Command.COLOR)

    def set_hue(self, value: int) -> None:
        self._send_set_command(Command.HUE, data=value)

    def get_hue(self):
        return self._send_get_command(Command.HUE)

    def set_sharpness(self, value: int) -> None:
        self._send_set_command(Command.SHARPNESS, data=value)

    def get_sharpness(self):
        return self._send_get_command(Command.SHARPNESS)

    def get_lamptimer(self) -> int:
        return self._send_get_command(Command.GET_STATUS_LAMP_TIMER)

    def get_rom_version(self) -> tuple[int, int]:
        versionCode = self._send_get_command(Command.GET_ROM_VERSION)
        minor = versionCode & 255
        major = versionCode >> 8
        return (major, minor)

    def get_sc_rom_version(self) -> tuple[int, int]:
        versionCode = self._send_get_command(Command.GET_SC_ROM_VERSION)
        minor = versionCode & 255
        major = versionCode >> 8
        return (major, minor)

    def get_nvm_data_version(self) -> int:
        return self._send_get_command(Command.GET_NVM_DATA_VERSION)

    def press_right(self) -> None:
        self._send_set_command(Command.BUTTON_RIGHT)

    def press_left(self) -> None:
        self._send_set_command(Command.BUTTON_LEFT)

    def press_up(self) -> None:
        self._send_set_command(Command.BUTTON_UP)

    def press_down(self) -> None:
        self._send_set_command(Command.BUTTON_DOWN)

    def press_menu(self) -> None:
        self._send_set_command(Command.BUTTON_MENU)

    def press_enter(self) -> None:
        self._send_set_command(Command.BUTTON_ENTER)

    def press_reset(self) -> None:
        self._send_set_command(Command.BUTTON_RESET)
