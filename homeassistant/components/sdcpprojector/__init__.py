"""The Sony Projector integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .protocol import ErrorCode, ErrorStatus
from .pysdcp import Projector, ProjectorException, ProjectorInfo, async_find_projector

_LOGGER = logging.getLogger(__name__)
ICON = "mdi:projector"


PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SELECT,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sony Projector from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    # projectors = [Projector(info) for info in await async_find_projector()]
    projectors = (Projector(ProjectorInfo(*info)) for info in entry.data["devices"])
    hass.data[DOMAIN][entry.entry_id] = dict()
    for projector in projectors:
        hass.data[DOMAIN][entry.entry_id][projector.info.serial_number] = (
            SdcpCoordinator(hass, projector, 30)
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class SdcpCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(
        self, hass: HomeAssistant, projector: Projector, interval: float
    ) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="SdcpProjector",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=interval),
        )
        self.power = False
        self.contrast = 50
        self.brightness = 50
        self.color = 50
        self.hue = 50
        self.sharpness = 50
        self.projector = projector
        self.available = False
        self.rom_version = (0, 0)
        self.sc_rom_version = (0, 0)
        self.nvm_data_version = 0
        self.error = ErrorStatus.NO_ERROR
        self.lamp_timer = -1
        self._last_update = datetime.min
        self.input = None
        self.device = DeviceInfo(
            identifiers={(DOMAIN, projector.info.serial_number)},
            manufacturer="SONY",
            name=projector.info.product_name,
            sw_version=projector.info.version,
            configuration_url="http://" + self.projector.info.ip,
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            self.power = self.projector.get_power()
            self.available = True
            if (datetime.now() - self._last_update).total_seconds() > 60 * 60 * 24:
                self.rom_version = self.projector.get_rom_version()
                self.sc_rom_version = self.projector.get_sc_rom_version()
                self.nvm_data_version = self.projector.get_nvm_data_version()
                self.device["hw_version"] = (
                    str(self.rom_version[0]) + "." + str(self.rom_version[1])
                )
                self.device["sw_version"] = (
                    str(self.sc_rom_version[0]) + "." + str(self.sc_rom_version[1])
                )
            self.error = self.projector.get_error()
            self.lamp_timer = self.projector.get_lamptimer()
            self._last_update = datetime.now()
            if self.power.is_on:
                self.contrast = self.projector.get_contrast()
                self.brightness = self.projector.get_brightness()
                self.color = self.projector.get_color()
                self.hue = self.projector.get_hue()
                self.sharpness = self.projector.get_sharpness()
                self.input = self.projector.get_input()
        # except ApiAuthError as err:
        # Raising ConfigEntryAuthFailed will cancel future updates
        # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #    raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        #    raise UpdateFailed(f"Error communicating with API: {err}")
        except ProjectorException as pexc:
            if pexc.error_code is ErrorCode.NOT_APPLICABLE_ITEM:
                pass
            raise UpdateFailed(f"Error received: {pexc}") from pexc
        except Exception as exc:
            self.available = False
            raise UpdateFailed(f"Error communicating with API: {exc}") from exc
