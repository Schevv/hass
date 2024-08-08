from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .controller import RhasspyDeviceController

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Rhasspy control."""
    controller = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([RhasspyVolumeNumberEntity(controller)], True)


class RhasspyVolumeNumberEntity(CoordinatorEntity, NumberEntity):
    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller)
        self.device_controller = device_controller
        self._attr_device_info = device_controller.device
        self._attr_assumed_state = False
        self._attr_available = True
        self._attr_has_entity_name = True
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_native_value = 100
        self._attr_icon = "mdi:volume-medium"
        self._attr_should_poll = False
        self._attr_unique_id = device_controller.unique_id + "-volume"
        self._attr_name = "Volume"

    @property
    def available(self) -> bool:
        return self.device_controller.data.available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_value = int(self.coordinator.data.volume)
        self._attr_native_value = int(self.coordinator.data.volume)
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Updates the current value"""
        await self.device_controller.async_set_volume(value)
        # await self.coordinator.async_post(
        #    "set-volume", data=str(value / 100.0), timeout=1
        # )
