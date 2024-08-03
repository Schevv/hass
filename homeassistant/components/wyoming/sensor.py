"""Sensor entities for Wyoming integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .devices import SatelliteDevice
from .entity import WyomingSatelliteEntity

if TYPE_CHECKING:
    from .models import DomainDataItem

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wyoming sensor entities."""
    item: DomainDataItem = hass.data[DOMAIN][config_entry.entry_id]

    # Setup is only forwarded for satellites
    assert item.satellite is not None

    device = item.satellite.device
    async_add_entities(
        [
            WyomingSatelliteLastNotification(device),
            WyomingSatelliteCpuLoad(device),
        ]
    )

class WyomingSatelliteLastNotification(WyomingSatelliteEntity, SensorEntity):
    """Entity to represent the last notification."""

    entity_description = SensorEntityDescription(
        key="last_notification",
        translation_key="last_notification",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, device: SatelliteDevice) -> None:
        """Initialize entity."""
        super().__init__(device)
        device.set_last_notification_listener(self._last_notification_updated)

    def _last_notification_updated(self, message: str, title: str) -> None:
        _LOGGER.warning("_last_notification_updated: %s %s", message, title)
        self._attr_native_value = message
        self._attr_extra_state_attributes = {'title': title}
        self.schedule_update_ha_state(True)


class WyomingSatelliteSensor(WyomingSatelliteEntity, SensorEntity):
    """Base for entity to represent satellite system stats."""

    def __init__(self, device: SatelliteDevice) -> None:
        """Initialize entity."""
        super().__init__(device)
        device.add_system_stats_listener(self.update_stats)

    async def update_stats(self, stats: dict[str, Any]) -> None:
        """Update the state of the entity from the stats dict."""
        self.update_state_from_stats(stats)
        self.async_update_ha_state()

    def update_state_from_stats(self, stats: dict[str, Any]) -> None:
        """Implement the actual update."""


class WyomingSatelliteCpuLoad(WyomingSatelliteSensor):
    """Entity to represent CPU load average on the satellite."""

    entity_description = SensorEntityDescription(
        key="cpu_load",
        translation_key="cpu_load",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        state_class=SensorStateClass.MEASUREMENT,
    )

    def update_state_from_stats(self, stats: dict[str, Any]) -> None:
        """Implement the actual update."""
        load_avg = stats.get("load_avg")
        cpu_count = stats.get("cpu_count")
        self._attr_native_value = float(load_avg[0]) / cpu_count
        self._attr_extra_state_attributes = {"cpucount": cpu_count}


