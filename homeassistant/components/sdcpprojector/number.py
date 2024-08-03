from __future__ import annotations

import itertools
import logging
import string
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iRobot Roomba vacuum cleaner."""
    coordinators = hass.data[DOMAIN][config_entry.entry_id].values()
    new_entities = itertools.chain(
        *[
            [
                SdcpGeneralNumberEntity(coordinator, "contrast", "mdi:contrast-circle"),
                SdcpGeneralNumberEntity(coordinator, "brightness", "mdi:brightness-5"),
                SdcpGeneralNumberEntity(coordinator, "color", "mdi:invert-colors"),
                SdcpGeneralNumberEntity(coordinator, "hue", "mdi:palette"),
                SdcpGeneralNumberEntity(coordinator, "sharpness", "mdi:blur"),
            ]
            for coordinator in coordinators
        ]
    )
    async_add_entities(
        new_entities,
        True,
    )


class SdcpGeneralNumberEntity(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, name: string, icon) -> None:
        super().__init__(coordinator)
        self._propname = name
        self._attr_device_info = coordinator.device
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_has_entity_name = True
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_native_value = 50
        self._attr_is_on = True
        self._attr_unique_id = (
            str(coordinator.projector.info.serial_number) + "sdcp-" + name
        )
        self._attr_name = name.capitalize()
        self._attr_icon = icon

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = getattr(self.coordinator, self._propname)
        self.async_write_ha_state()

    def set_native_value(self, value: float) -> None:
        """Update the current value."""
        getattr(self.coordinator.projector, "set_" + self._propname)(int(value))
