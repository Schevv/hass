from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iRobot Roomba vacuum cleaner."""
    coordinators = hass.data[DOMAIN][config_entry.entry_id].values()
    async_add_entities(
        [SdcpPowerSwitchEntity(coordinator) for coordinator in coordinators], True
    )


class SdcpPowerSwitchEntity(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device
        self._attr_unique_id = (
            str(coordinator.projector.info.serial_number) + "sdcp-pwr"
        )
        self._attr_has_entity_name = True
        self._attr_name = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.power.is_on
        self._attr_available = self.coordinator.available
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on.

        Example method how to request data updates.
        """
        self.coordinator.projector.set_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light on.

        Example method how to request data updates.
        """
        self.coordinator.projector.set_power(False)
        await self.coordinator.async_request_refresh()
