"""Sensors for SDCP Projector"""

from __future__ import annotations

import itertools
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
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
    new_entities = itertools.chain(
        *[
            [SdcpLampTimerEntity(coordinator), SdcpErrorStatusEntity(coordinator)]
            for coordinator in coordinators
        ]
    )
    async_add_entities(
        new_entities,
        True,
    )


class SdcpLampTimerEntity(CoordinatorEntity, SensorEntity):
    """Sensor entity showing the number of hours the lamp is in use"""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_unique_id = (
            str(coordinator.projector.info.serial_number) + "sdcp-lamptimer"
        )
        self._attr_has_entity_name = True
        self._attr_name = "Lamptimer"
        self._attr_device_class = "duration"
        self._attr_native_unit_of_measurement = "h"
        self._attr_state_class = "total_increasing"
        self._attr_icon = "mdi:lightbulb"
        self._attr_unit_of_measurement = "h"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.lamp_timer >= 0:
            self._attr_native_value = self.coordinator.lamp_timer
        self.async_write_ha_state()


class SdcpErrorStatusEntity(CoordinatorEntity, SensorEntity):
    """Sensor showing the current status of the projector"""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_unique_id = (
            str(coordinator.projector.info.serial_number) + "sdcp-status"
        )
        self._attr_has_entity_name = True
        self._attr_name = "Status"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = str(self.coordinator.error)
        self.async_write_ha_state()
