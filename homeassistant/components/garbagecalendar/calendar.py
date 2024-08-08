from datetime import date, datetime
import json
import logging

import requests

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import now

from .const import DOMAIN, URL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iRobot Roomba vacuum cleaner."""
    async_add_entities(
        [
            GarbageCalendar(
                config_entry.entry_id, hass.data[DOMAIN][config_entry.entry_id]
            )
        ],
        True,
    )


class GarbageCalendar(CoordinatorEntity, CalendarEntity):
    def __init__(self, unique_id, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._event: CalendarEvent = None
        self._attr_name = None  # "Müllkalender"
        self._attr_has_entity_name = True
        # self._last_update = datetime.min
        self._attr_device_info = coordinator.device
        self.events = self.coordinator.events
        self._event = self.coordinator.next_event
        _LOGGER.debug("Calender init done")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("Calendar doing coordinator update")
        self.events = self.coordinator.events
        self._event = self.coordinator.next_event
        self.async_write_ha_state()

    def set_native_value(self, value: float) -> None:
        """Update the current value."""

    @property
    def event(self) -> CalendarEvent:
        """Return the next upcoming event."""
        return self._event

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""

        def check_in_bounds(event: CalendarEvent):
            return (
                event.start.toordinal() >= start_date.toordinal()
                and event.end.toordinal() <= end_date.toordinal()
            )

        return [event for event in self.events if check_in_bounds(event)]


class GarbageCalendar2(CalendarEntity):
    """A device for getting the next Task from a WebDav Calendar."""

    def __init__(self, unique_id) -> None:
        """Create the WebDav Calendar Event Device."""
        # self.data = WebDavCalendarData(calendar, days, all_day, search)
        # self.entity_id = entity_id
        self._attr_unique_id = unique_id
        self._event: CalendarEvent = None
        self._attr_name = "Müllkalender"
        self._attr_has_entity_name = True
        self._last_update = datetime.min
        self.events = []

    @property
    def event(self) -> CalendarEvent:
        """Return the next upcoming event."""
        return self._event

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""

        def check_in_bounds(event: CalendarEvent):
            return (
                event.start.toordinal() >= start_date.toordinal()
                and event.end.toordinal() <= end_date.toordinal()
            )

        return [event for event in self.events if check_in_bounds(event)]

    def update(self) -> None:
        """Update event data."""
        if (datetime.now() - self._last_update).total_seconds() < 60 * 60 * 24:
            return
        self._last_update = datetime.now()

        response = requests.get(
            URL,
            timeout=2,
        )
        if response.status_code != 200:
            _LOGGER.warning("Error calling web API: %s", response.text)
        else:
            data = json.loads(response.text)
            names = {x["snm"]: x["nm"] for x in data["fracts"]}
            events = []
            for event in data["calendar"]:
                dtstr = event["dt"]
                start = date(int(dtstr[0:4]), int(dtstr[4:6]), int(dtstr[6:8]))
                if event["ft"]:
                    events.append(CalendarEvent(start, start, event["ft"]))
                if event["fr"]:
                    for fr in event["fr"]:
                        events.append(CalendarEvent(start, start, names[fr]))
            events.sort(key=lambda x: x.start.toordinal())
            self.events = events
            self._event = next(
                (e for e in events if e.start.toordinal() >= now().toordinal()), None
            )
