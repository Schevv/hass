from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .controller import RhasspyDeviceController

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Rhasspy control."""
    controller = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            ListenForWakeRhasspyControlEntity(controller),
            SpeakNotificationsRhasspyControlEntity(controller),
            SignalOnlyNotificationsRhasspyControlEntity(controller),
        ],
        True,
    )


class RhasspySwitch(CoordinatorEntity, SwitchEntity):
    """Base class for switches"""

    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller)
        self.device_controller = device_controller
        self._attr_device_info = device_controller.device
        self._attr_assumed_state = False
        self._attr_has_entity_name = True

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.device_controller.data.available


class SpeakNotificationsRhasspyControlEntity(RhasspySwitch, RestoreEntity):
    """Switch that controls if this Rhasspy instance will output notification."""

    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller)
        self._attr_icon = "mdi:message-outline"
        self._attr_unique_id = device_controller.unique_id + "-ttsnotify"
        self._attr_name = "Notification"

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        self._attr_is_on = state.state == STATE_ON
        self.device_controller.tts_notification_switch = self

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self._attr_is_on = False
        self.async_write_ha_state()


class SignalOnlyNotificationsRhasspyControlEntity(RhasspySwitch, RestoreEntity):
    """Switch that controls if this Rhasspy instance will output notification as text or sound."""

    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller)
        self._attr_icon = "mdi:message-outline"
        self._attr_unique_id = device_controller.unique_id + "-ttsnotify-as-sound"
        self._attr_name = "Notification as Sound"

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        self._attr_is_on = state.state == STATE_ON
        self.device_controller.tts_notification_sound_switch = self

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self._attr_is_on = False
        self.async_write_ha_state()


class ListenForWakeRhasspyControlEntity(RhasspySwitch):
    """Button to start/stop listening for the wake word"""

    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller)
        self._attr_icon = "mdi:power"
        self._attr_unique_id = device_controller.unique_id + "-listen-wake"
        self._attr_name = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.data.listening
        self._attr_available = True
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.device_controller.async_post(
            "listen-for-wake", data="on", timeout=10
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.device_controller.async_post(
            "listen-for-wake", data="off", timeout=10
        )
