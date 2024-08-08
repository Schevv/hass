"""Switches for AVM Fritz!Box buttons."""

from __future__ import annotations

import importlib.resources
import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import sounds
from .const import DOMAIN, SOUNDS
from .controller import RhasspyDeviceController

_LOGGER = logging.getLogger(__name__)


class RhasspyControlButton(CoordinatorEntity, ButtonEntity):
    """Base class for all buttons of this integration"""

    def __init__(
        self, device_controller: RhasspyDeviceController, name: str, icon: str
    ) -> None:
        super().__init__(device_controller, None)
        self.device_controller = device_controller
        self._attr_device_info = device_controller.device
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_available = True
        if icon is not None:
            self._attr_icon = icon
        self._attr_should_poll = False
        self._attr_unique_id = (
            device_controller.unique_id + "-" + name.replace(" ", "-").lower()
        )

    @property
    def available(self) -> bool:
        return self.device_controller.data.available


class NotificationRhasspyControlButton(RhasspyControlButton):
    """Button to sound an acoustic notification"""

    def __init__(self, device_controller) -> None:
        super().__init__(device_controller, "Ring", "mdi:bell")

    async def async_press(self) -> None:
        """Handle the button press."""
        sound_filename = SOUNDS[self.device_controller.selected_ringer_sound]
        with importlib.resources.open_binary(sounds, sound_filename) as sound_data:
            buffered_sound_data = sound_data.read()
        await self.device_controller.async_post(
            "play-wav", headers={"Content-Type": "audio/wav"}, data=buffered_sound_data
        )


class TestSuccessSoundRhasspyControlButton(RhasspyControlButton):
    """Button to sound the acoustic notification for success"""

    def __init__(self, device_controller) -> None:
        super().__init__(device_controller, "Test Success Sound", "mdi:check-circle")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Handle the button press."""
        sound_filename = SOUNDS[self.device_controller.selected_success_sound]
        with importlib.resources.open_binary(sounds, sound_filename) as sound_data:
            buffered_sound_data = sound_data.read()
        await self.device_controller.async_post(
            "play-wav", headers={"Content-Type": "audio/wav"}, data=buffered_sound_data
        )


class ListenForCommandRhasspyControlButton(RhasspyControlButton):
    """Button to skip wake word detection and directly start listening for a command"""

    def __init__(self, device_controller) -> None:
        super().__init__(device_controller, "Start Listening", "mdi:account-voice")

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.device_controller.async_post("listen-for-command", timeout=10)


class RetrainRhasspyControlButton(RhasspyControlButton):
    """Button to start retraining of Rhasspy"""

    def __init__(self, device_controller) -> None:
        super().__init__(device_controller, "Retrain", "mdi:autorenew")
        self._attr_entity_category = "config"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.device_controller.async_post("train", timeout=10)


class RestartRhasspyControlButton(RhasspyControlButton):
    """Button to restart Rhasspy"""

    def __init__(self, device_controller) -> None:
        super().__init__(device_controller, "Restart", "mdi:restart")
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_class = ButtonDeviceClass.RESTART

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.device_controller.async_post("restart", timeout=10)


class ReplayRhasspyControlButton(RhasspyControlButton):
    """Button to replay the last command spoken"""

    def __init__(self, device_controller) -> None:
        super().__init__(
            device_controller, "Replay last command", "mdi:play-circle-outline"
        )
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.device_controller.async_post("play-recording", timeout=10)


class ReplayOutputRhasspyControlButton(RhasspyControlButton):
    """Button to replay last output from Rhasspy"""

    def __init__(self, device_controller) -> None:
        super().__init__(
            device_controller, "Replay last output", "mdi:play-circle-outline"
        )
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.device_controller.async_post(
            "text-to-speech?repeat=true", timeout=10
        )


class SpeakLastNotificationRhasspyControlButton(RhasspyControlButton):
    """Button to speak the last notification."""

    def __init__(self, device_controller) -> None:
        super().__init__(device_controller, "Speak Notification", "mdi:message-text")

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.device_controller.speak_last_notification()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set buttons for device."""

    device_controller = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            ListenForCommandRhasspyControlButton(device_controller),
            # RetrainRhasspyControlButton(device_controller),
            RestartRhasspyControlButton(device_controller),
            ReplayRhasspyControlButton(device_controller),
            ReplayOutputRhasspyControlButton(device_controller),
            NotificationRhasspyControlButton(device_controller),
            TestSuccessSoundRhasspyControlButton(device_controller),
            SpeakLastNotificationRhasspyControlButton(device_controller),
        ],
        True,
    )
