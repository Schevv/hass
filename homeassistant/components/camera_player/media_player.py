"""Support to interact with a Music Player Daemon."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import media_source
from homeassistant.components.camera import DOMAIN as DOMAIN_CAMERA
from homeassistant.components.media_player import (
    DOMAIN as DOMAIN_MEDIA_PLAYER,
    BrowseMedia,
    MediaPlayerEnqueue,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
    async_process_play_media_url,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .camera import CameraPlayerCamera
from .const import DOMAIN

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
    entity = CameraPlayerMediaPlayer(name, unique_id)
    hass.data[DOMAIN][config_entry.entry_id][DOMAIN_MEDIA_PLAYER] = entity
    async_add_entities([entity])



class CameraPlayerMediaPlayer(MediaPlayerEntity):
    """Media player of the Camera Player."""

    def __init__(self, device_name: str, uid: str) -> None:
        """Initialize the player."""
        self._attr_device_info = DeviceInfo(name=device_name, identifiers={(DOMAIN, uid)})
        self._attr_has_entity_name = True
        self._attr_should_poll = False
        self._attr_supported_features = MediaPlayerEntityFeature.BROWSE_MEDIA | MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.PLAY | MediaPlayerEntityFeature.STOP
        self._attr_unique_id = "M" + uid
        self._attr_state = MediaPlayerState.IDLE
        self._attr_media_content_type = MediaType.MOVIE
        self._camera : CameraPlayerCamera = None
        self.current_stream : str | None = None # TODO: Replace with playlist

    @property
    def camera(self) -> CameraPlayerCamera | None:
        """Return the media player associated with this camera."""
        if not self._camera:
            self._camera = self.hass.data[DOMAIN][self.unique_id[1:]][DOMAIN_CAMERA]
        return self._camera

    @property
    def state(self) -> MediaPlayerState | None:
        """State of the player."""
        return self._attr_state

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        self._attr_state = MediaPlayerState.IDLE
        self.async_schedule_update_ha_state()

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        self.current_stream = None
        self._attr_media_content_type = None
        self._attr_state = MediaPlayerState.OFF
        await self.camera.set_source_stream(None)
        self.async_schedule_update_ha_state()

    async def async_browse_media(
        self, media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None
    ) -> BrowseMedia:
        """Implement the websocket media browsing helper."""
        # If your media player has no own media sources to browse, route all browse commands
        # to the media source integration.
        _LOGGER.warning("Browsing media %s")
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            # This allows filtering content. In this case it will only show audio sources.
            content_filter=lambda item: True,
        )

    async def async_play_media(
        self,
        media_type: MediaType | str,
        media_id: str,
        enqueue: MediaPlayerEnqueue | None = None,
        announce: bool | None = None, **kwargs: Any
    ) -> None:
        """Play a piece of media."""
        if media_source.is_media_source_id(media_id):
            play_item = await media_source.async_resolve_media(self.hass, media_id, self.entity_id)
            # play_item returns a relative URL if it has to be resolved on the Home Assistant host
            # This call will turn it into a full URL
            media_id = async_process_play_media_url(self.hass, play_item.url)

        _LOGGER.warning("Playing media %s", media_id)

        # Replace this with calling your media player play media function.
        self.current_stream = media_id
        self._attr_media_content_type = MediaType.MOVIE if media_id is not None else None
        self._attr_state = MediaPlayerState.PLAYING
        await self.camera.set_source_stream(self.current_stream)
        self.async_schedule_update_ha_state()

