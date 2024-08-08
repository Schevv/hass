"""Sensor entities for Wyoming integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
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
            WyomingSatelliteVirtualMemory(device),
            WyomingSatelliteDiskMemory(device),
            WyomingSatelliteTemperature(device),
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
        self._attr_native_value = message
        self._attr_extra_state_attributes = {"title": title}
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
        self.schedule_update_ha_state()

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


class WyomingSatelliteVirtualMemory(WyomingSatelliteSensor):
    """Entity to represent CPU load average on the satellite."""

    entity_description = SensorEntityDescription(
        key="vmem",
        translation_key="vmem",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement="B",
        suggested_unit_of_measurement="MB",
    )

    def update_state_from_stats(self, stats: dict[str, Any]) -> None:
        """Implement the actual update."""
        vmem = stats.get("vmem")
        if vmem is not None:
            total = vmem.get("total")
            available = vmem.get("available")
            free = vmem.get("free")
            self._attr_native_value = int(available)
            self._attr_extra_state_attributes = {"total": int(total), "free": int(free)}


class WyomingSatelliteDiskMemory(WyomingSatelliteSensor):
    """Entity to represent CPU load average on the satellite."""

    entity_description = SensorEntityDescription(
        key="disk_mem",
        translation_key="disk_mem",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement="B",
        suggested_unit_of_measurement="GB",
    )

    def update_state_from_stats(self, stats: dict[str, Any]) -> None:
        """Implement the actual update."""
        mem = stats.get("disk", stats.get("disks"))
        if mem is not None:
            total = mem.get("total")
            used = mem.get("used")
            free = mem.get("free")
            self._attr_native_value = int(free)
            self._attr_extra_state_attributes = {"total": int(total), "used": int(used)}


class WyomingSatelliteTemperature(WyomingSatelliteSensor):
    """Entity to represent CPU load average on the satellite."""

    entity_description = SensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
    )

    def update_state_from_stats(self, stats: dict[str, Any]) -> None:
        """Implement the actual update."""
        temp = stats.get("temperature")
        if temp is not None:
            current = temp.get("current")
            high = temp.get("high")
            critical = temp.get("critical")
            self._attr_native_value = float(current)
            self._attr_extra_state_attributes = {
                "high": int(high),
                "critical": int(critical),
            }
