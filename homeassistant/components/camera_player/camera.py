"""Support for a camera of a BloomSky weather station."""
from __future__ import annotations

import logging

from homeassistant.components.camera import (
    DOMAIN as DOMAIN_CAMERA,
    Camera,
    CameraEntityFeature,
)
from homeassistant.components.media_player import (
    DOMAIN as DOMAIN_MEDIA_PLAYER,
    MediaPlayerEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Camera Player config entry."""
    name = config_entry.title
    unique_id = config_entry.entry_id

    _LOGGER.warning("Adding Camera %s %s", name, unique_id)
    entity = CameraPlayerCamera(name, unique_id)
    hass.data[DOMAIN][config_entry.entry_id][DOMAIN_CAMERA] = entity
    async_add_entities([entity])


class CameraPlayerCamera(Camera):
    """Representation of the images published from the BloomSky's camera."""

    def __init__(self, device_name: str, uid: str) -> None:
        """Initialize access to the BloomSky camera images."""
        super().__init__()
        self._attr_name = "Display"
        self._attr_device_info = DeviceInfo(name=device_name, identifiers={(DOMAIN, uid)})
        self._attr_has_entity_name = True
        self._attr_unique_id = "C_" + uid
        self._attr_supported_features = CameraEntityFeature.ON_OFF | CameraEntityFeature.STREAM
        self._current_stream : str | None = None
        self._media_player : CameraPlayerCamera | None = None

    async def set_source_stream(self, stream: str | None) -> None:
        """Set the stream to display."""
        self._current_stream = stream
        self.async_schedule_update_ha_state()

    @property
    def is_on(self) -> bool:
        """Returns if the camera is turned on."""
        return self._current_stream is not None

    @property
    def is_streaming(self) -> bool:
        """Returns if the camera is streaming on."""
        return self.is_on

    @property
    def use_stream_for_stills(self) -> bool:
        """Whether or not to use stream to generate stills."""
        return True

    @property
    def media_player(self) -> MediaPlayerEntity | None:
        """Return the media player associated with this camera."""
        if not self._media_player:
            self._media_player = self.hass.data[DOMAIN][self.unique_id[1:]][DOMAIN_MEDIA_PLAYER]
        return self._media_player

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        return self._current_stream

    async def async_turn_on(self) -> None:
        """Turn on camera."""
        if self.media_player:
            await self.media_player.async_turn_on()

    async def async_turn_off(self) -> None:
        """Turn on camera."""
        if self.media_player:
            await self.media_player.async_turn_off()
