from datetime import date, datetime
import json
import logging

import requests

from .const import DOMAIN

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.components.sensor.const import SensorDeviceClass
from . import GarbageCalendarCoordinator
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import now
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=15)
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iRobot Roomba vacuum cleaner."""
    async_add_entities(
        [
            GarbageCalendarSensor(
                config_entry, hass.data[DOMAIN][config_entry.entry_id], "R"
            ),
            GarbageCalendarSensor(
                config_entry, hass.data[DOMAIN][config_entry.entry_id], "B"
            ),
            GarbageCalendarSensor(
                config_entry, hass.data[DOMAIN][config_entry.entry_id], "P"
            ),
            GarbageCalendarSensor(
                config_entry, hass.data[DOMAIN][config_entry.entry_id], "W"
            ),
        ],
        True,
    )


class GarbageCalendarSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: GarbageCalendarCoordinator,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._type_key = key
        self._attr_unique_id = config_entry.unique_id + key
        self._attr_device_info = coordinator.device
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "d"
        self._attr_suggested_unit_of_measurement = "d"
        self.long_name = coordinator.names[key]
        self._attr_name = coordinator.names[key]

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Handling coordinator update for %s", self._attr_name)
        events = [
            e
            for e in self.coordinator.events
            if e.start.toordinal() >= now().toordinal() and e.summary == self.long_name
        ]
        _LOGGER.debug("Found %s events for %s", len(events), self._attr_name)
        if len(events) == 0:
            self._attr_native_value = -1
        else:
            next_event = events[0]
            next_date = date(
                next_event.start.year, next_event.start.month, next_event.start.day
            )
            duration = next_date - date.today()
            self._attr_native_value = duration.days
        self.async_write_ha_state()
