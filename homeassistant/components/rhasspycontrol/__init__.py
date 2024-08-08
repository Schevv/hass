"""The Rhasspy Control integration."""

from __future__ import annotations

import asyncio
import importlib.resources
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import discovery, entity_registry
from homeassistant.helpers.service import async_extract_config_entry_ids
from homeassistant.helpers.typing import ConfigType

from . import sounds
from .const import DOMAIN, SOUNDS
from .controller import RhasspyDeviceController

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.NOTIFY,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


# Service: TextOutput
# ???: Play wav
# ???: Process wav
# ???: Download last command


# Switch: Listen-for-wake-word
# Number: Volume
# Button: Listen-for-command
# Button: Play back last command
# (Button: Retrain)
# Button: Restart


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the REST command component."""

    async def async_get_rhasspy_controllers(
        service: ServiceCall,
    ) -> set[RhasspyDeviceController]:
        config_entry_ids = await async_extract_config_entry_ids(hass, service)

        if len(config_entry_ids) == 0:
            entities = entity_registry.async_get(hass)
            config_entry_ids = [
                entity_entry.config_entry_id
                for entity_entry in entities.entities.values()
                if entity_entry.platform == DOMAIN
            ]

        controllers = {
            hass.data[DOMAIN].get(config_entry, None)
            for config_entry in config_entry_ids
        }
        controllers = {
            controller
            for controller in controllers
            if controller is not None
            and isinstance(controller, RhasspyDeviceController)
        }
        return controllers

    async def async_soundoutput_service_handler(service: ServiceCall) -> None:
        default_name = "Notification"

        attribution = {
            "Notification": "https://orangefreesounds.com/",
        }

        controllers = await async_get_rhasspy_controllers(service)

        sound = service.data.get("sound", None)
        if sound is None:
            sound = default_name

        for controller in controllers:
            if sound == "SUCCESS":
                sound = controller.selected_success_sound
            sound = SOUNDS.get(sound, None)
            if sound is None:
                raise ValueError("Unkown sound")

            tasks = []
            with importlib.resources.open_binary(sounds, sound) as sound_data:
                data = sound_data.read()
                await controller.async_post(
                    "play-wav",
                    headers={"Content-Type": "audio/wav"},
                    data=data,
                )

    async def async_textoutput_service_handler(service: ServiceCall) -> None:
        controllers = await async_get_rhasspy_controllers(service)

        if len(controllers) == 0:
            raise ValueError("No Rhasspy Control instances found")

        await asyncio.wait(
            [
                asyncio.create_task(
                    controller.tts_speak(
                        service.data.get("text", ""),
                        voice=service.data.get("voice", None),
                        language=service.data.get("language", None),
                        repeat=service.data.get("repeat", False),
                        volume=service.data.get("volume", None),
                        siteid=service.data.get("siteid", None),
                    ),
                    name="Rhasspy Speak Service Call",
                )
                for controller in controllers
            ]
        )

    hass.services.async_register(
        DOMAIN, "text_to_speech", async_textoutput_service_handler
    )
    hass.services.async_register(
        DOMAIN, "play_sound", async_soundoutput_service_handler
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rhasspy Control from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = RhasspyDeviceController(hass, entry, entry.data)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # set up notify platform, no entry support for notify component yet,
    # have to use discovery to load platform.
    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            Platform.NOTIFY,
            DOMAIN,
            {"controller": hass.data[DOMAIN][entry.entry_id]},
            entry.data,
        )
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
