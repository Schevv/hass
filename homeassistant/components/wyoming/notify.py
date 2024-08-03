"""Wyoming notify entities."""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.notify import NotifyEntity, NotifyEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import restore_state
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import WyomingSatelliteEntity

if TYPE_CHECKING:
    from .models import DomainDataItem

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up VoIP switch entities."""
    item: DomainDataItem = hass.data[DOMAIN][config_entry.entry_id]

    # Setup is only forwarded for satellites
    assert item.satellite is not None

    async_add_entities([WyomingSatelliteNotify(item.satellite.device)])


class WyomingSatelliteNotify(
    WyomingSatelliteEntity, NotifyEntity
):
    """Entity to trigger a stt notification on the satellite."""

    entity_description = NotifyEntityDescription(
        key="notify",
        translation_key="notify",
    )

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a message."""
        self._device.set_last_notification(message, title)
        if self._device.notificationtone is not None:
            self._device.play_notificationtone(self.hass)
        else:
            self._device.tts_play(message)
