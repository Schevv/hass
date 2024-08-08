"""The GarbageCalendar integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import logging

import requests

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import now

from .const import (
    DEVICE_IDENTIFIER,
    DOMAIN,
    FETCH_TIMEOUT,
    UPDATE_INTERVAL_SECONDS,
    URL,
)
from .garbage_news import GarbageNews

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GarbageCalendar from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    # TODO 1. Create API instance
    # TODO 2. Validate the API connection (and authentication)
    # TODO 3. Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    # hass.data[DOMAIN][entry.entry_id] = dict()

    coordinator = GarbageCalendarCoordinator(hass, UPDATE_INTERVAL_SECONDS)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class GarbageCalendarCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, interval: float) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="GarbageCalendar",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=1),
        )
        self._last_update = datetime.min
        self.events = []
        self.next_event = None
        self.next_events = {}
        self.news = []
        self.names = {}
        self.device = DeviceInfo(
            identifiers={(DOMAIN, DEVICE_IDENTIFIER)},
            manufacturer="Cube FOUR GmbH",
            name="Müllkalender",
            configuration_url="https://awido.cubefour.de/Customer/eww-suew/mobile/",
        )
        self.normal_interval = interval
        _LOGGER.debug("Coordinator setup done")

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        _LOGGER.debug("Coordinator updating")
        self._last_update = datetime.now()
        self.update_interval = timedelta(UPDATE_INTERVAL_SECONDS)

        await self.hass.async_add_executor_job(self._sync_update)

    def _sync_update(self):
        _LOGGER.debug("Starting sync update")
        response = requests.get(
            URL,
            timeout=FETCH_TIMEOUT,
        )
        today = date.today()
        if response.status_code != 200:
            _LOGGER.warning("Error calling web API: %s", response.text)
        else:
            data = json.loads(response.text)
            self.names = {x["snm"]: x["nm"] for x in data["fracts"]}
            _LOGGER.debug("Read %s names: %s", len(self.names), list(self.names.keys()))
            next_dates = {x["snm"]: date.max for x in data["fracts"]}
            events = []
            for event in data["calendar"]:
                dtstr = event["dt"]
                start = date(int(dtstr[0:4]), int(dtstr[4:6]), int(dtstr[6:8]))
                if event["ft"]:
                    events.append(
                        CalendarEvent(start, start + timedelta(days=1), event["ft"])
                    )
                    if start >= today and start < next_dates[fract]:
                        next_dates[fract] = start
                if event["fr"]:
                    for fract in event["fr"]:
                        events.append(
                            CalendarEvent(
                                start, start + timedelta(days=1), self.names[fract]
                            )
                        )
                        if start >= today and start < next_dates[fract]:
                            next_dates[fract] = start
            events.sort(key=lambda x: x.start.toordinal())
            self.events = events
            _LOGGER.debug("Read %s events", len(self.events))
            self.next_event = next(
                (e for e in events if e.start.toordinal() >= now().toordinal()), None
            )

            updated_news = {
                x["id"]: GarbageNews(
                    x["id"],
                    date(int(x["dt"][0:4]), int(x["dt"][4:6]), int(x["dt"][6:8])),
                    x["t"],
                    x["z"],
                )
                for x in data["news"]
            }

        _LOGGER.debug("Sync update done")
