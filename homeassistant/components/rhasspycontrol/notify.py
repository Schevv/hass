"""Contains the entry point for the Rhasspy notifications."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.components.notify import BaseNotificationService, NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .controller import RhasspyDeviceController

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> RhasspyTtsNotificationService | None:
    """Get the notification service."""
    if discovery_info is None:
        _LOGGER.warning("Error setting up notification")
        return None

    return RhasspyTtsNotificationService(discovery_info["controller"])

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set buttons for device."""

    device_controller = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            RhasspyNotifier(device_controller)
        ],
        True,
    )


class RhasspyTtsNotificationService(BaseNotificationService):
    """Notifies via TTS to a Rhasspy Instance"""

    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        self.device_controller = device_controller

    @property
    def targets(self) -> Mapping[str, Any] | None:
        """Return a dictionary of registered targets."""
        return {self.device_controller.name: self.device_controller}

    async def async_send_message(self, message: str, **kwargs: Any) -> None:
        await self.device_controller.perform_tts_notification(message, **kwargs)

class RhasspyNotifier(NotifyEntity):
    """Entity to notify via TTS."""

    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        """Initialize."""
        super().__init__()
        self.device_controller = device_controller
        self._attr_device_info = device_controller.device
        self._attr_has_entity_name = True
        self._attr_name = "Notify"
        self._attr_available = True
        self._attr_should_poll = False
        self._attr_unique_id = (
            device_controller.unique_id + "-notify"
        )

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a message."""
        await self.device_controller.perform_tts_notification(message, title=title)
