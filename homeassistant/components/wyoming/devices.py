"""Class to manage satellite devices."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
import importlib.resources
import logging
from pathlib import Path
from typing import Any

from homeassistant.components.assist_pipeline.vad import VadSensitivity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from . import sounds
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class SatelliteDevice:
    """Class to store device."""

    satellite_id: str
    device_id: str
    is_active: bool = False
    is_muted: bool = False
    pipeline_name: str | None = None
    noise_suppression_level: int = 0
    auto_gain: int = 0
    volume_multiplier: float = 1.0
    vad_sensitivity: VadSensitivity = VadSensitivity.DEFAULT
    ringtone: str | None = None
    notificationtone: str | None = None
    last_notification: str | None = None

    _is_active_listener: Callable[[], None] | None = None
    _is_muted_listener: Callable[[], None] | None = None
    _pipeline_listener: Callable[[], None] | None = None
    _audio_settings_listener: Callable[[], None] | None = None
    _audio_play_listener: Callable[[bytes], None] | None = None
    _tts_play_listener: Callable[[str], None] | None = None
    _system_stats_listener: list[Callable[[dict[str, Any]], Coroutine]] = field(
        default_factory=list
    )
    _last_notification_listener: Callable[[str, str], None] | None = None

    @callback
    def tts_play(self, text: str) -> None:
        """Speak a text on a sattelite."""
        if self._tts_play_listener is not None:
            self._tts_play_listener(text)

    @callback
    def play_audio(self, wav_data: bytes) -> None:
        """Play WAV audio on a sattelite."""
        if self._audio_play_listener is not None:
            self._audio_play_listener(wav_data)

    @callback
    def set_is_active(self, active: bool) -> None:
        """Set active state."""
        if active != self.is_active:
            self.is_active = active
            if self._is_active_listener is not None:
                self._is_active_listener()

    @callback
    def set_is_muted(self, muted: bool) -> None:
        """Set muted state."""
        if muted != self.is_muted:
            self.is_muted = muted
            if self._is_muted_listener is not None:
                self._is_muted_listener()

    @callback
    def set_pipeline_name(self, pipeline_name: str) -> None:
        """Inform listeners that pipeline selection has changed."""
        if pipeline_name != self.pipeline_name:
            self.pipeline_name = pipeline_name
            if self._pipeline_listener is not None:
                self._pipeline_listener()

    @callback
    def set_noise_suppression_level(self, noise_suppression_level: int) -> None:
        """Set noise suppression level."""
        if noise_suppression_level != self.noise_suppression_level:
            self.noise_suppression_level = noise_suppression_level
            if self._audio_settings_listener is not None:
                self._audio_settings_listener()

    @callback
    def set_auto_gain(self, auto_gain: int) -> None:
        """Set auto gain amount."""
        if auto_gain != self.auto_gain:
            self.auto_gain = auto_gain
            if self._audio_settings_listener is not None:
                self._audio_settings_listener()

    @callback
    def set_volume_multiplier(self, volume_multiplier: float) -> None:
        """Set auto gain amount."""
        if volume_multiplier != self.volume_multiplier:
            self.volume_multiplier = volume_multiplier
            if self._audio_settings_listener is not None:
                self._audio_settings_listener()

    @callback
    def set_vad_sensitivity(self, vad_sensitivity: VadSensitivity) -> None:
        """Set VAD sensitivity."""
        if vad_sensitivity != self.vad_sensitivity:
            self.vad_sensitivity = vad_sensitivity
            if self._audio_settings_listener is not None:
                self._audio_settings_listener()

    @callback
    def set_ringtone(self, ringtone: str) -> None:
        """Set the ringtone."""
        if ringtone != self.ringtone:
            self.ringtone = ringtone

    @callback
    def set_notificationtone(self, notificationtone: str) -> None:
        """Set the ringtone."""
        if notificationtone != self.notificationtone:
            self.notificationtone = notificationtone

    def get_custom_sounds(self, hass: HomeAssistant) -> list[str]:
        """Return the extra sounds in the custom_sounds directory."""
        custom_sounds_dir = Path(hass.config.path("custom_sounds"))
        if custom_sounds_dir.is_dir():
            return [
                filename.stem
                for filename in custom_sounds_dir.rglob("*.wav")
                if filename.is_file()
            ]
        return []

    def get_default_sounds(self) -> list[str]:
        """Return the default sounds that come with the integration."""
        return [
            f.name[:-4]
            for f in importlib.resources.files(sounds).iterdir()
            if f.name.endswith(".wav")
        ]

    def get_sounds(self, hass: HomeAssistant) -> list[str]:
        """Return all available sound files."""
        cs = self.get_custom_sounds(hass)
        for s in self.get_default_sounds():
            if s not in cs:
                cs.insert(0, s)
        return cs

    def play_ringtone(self, hass: HomeAssistant) -> None:
        """Play the currently selected ringtone."""
        if self.ringtone is None:
            self.ringtone = self.get_sounds(hass)[0]
        data = self.get_sound_data(hass, self.ringtone)
        self.play_audio(data)

    def play_notificationtone(self, hass: HomeAssistant) -> None:
        """Play the currently selected notification."""
        if self.notificationtone is not None:
            data = self.get_sound_data(hass, self.notificationtone)
            self.play_audio(data)

    def get_notificationtone_data(self, hass: HomeAssistant) -> bytes:
        """Get the wav data for the currently selected notificationtone."""
        if self.notificationtone is None:
            self.ringtone = self.get_sounds()[0]
        return self.get_sound_data(hass, self.ringtone)

    def get_sound_data(self, hass: HomeAssistant, soundfile: str) -> bytes:
        """Get the wav data for the given sound name."""
        custom_sounds_dir = Path(hass.config.path("custom_sounds"))
        if custom_sounds_dir.is_dir():
            sound_path = custom_sounds_dir / (soundfile + ".wav")
            if sound_path.is_file():
                with sound_path.open("rb") as file:
                    return file.read()
        with (
            importlib.resources.files(sounds)
            .joinpath(soundfile + ".wav")
            .open("rb") as file
        ):
            return file.read()

    def set_last_notification(self, message: str, title: str) -> None:
        """Set last_notification."""
        self.last_notification = message
        if self._last_notification_listener is not None:
            self._last_notification_listener(message, title)

    @callback
    async def async_set_system_stats(self, stats: dict[str, Any]) -> None:
        """Set the new satellite system stats."""
        for listener in self._system_stats_listener:
            await listener(stats)

    @callback
    def set_is_active_listener(self, is_active_listener: Callable[[], None]) -> None:
        """Listen for updates to is_active."""
        self._is_active_listener = is_active_listener

    @callback
    def set_is_muted_listener(self, is_muted_listener: Callable[[], None]) -> None:
        """Listen for updates to muted status."""
        self._is_muted_listener = is_muted_listener

    @callback
    def set_pipeline_listener(self, pipeline_listener: Callable[[], None]) -> None:
        """Listen for updates to pipeline."""
        self._pipeline_listener = pipeline_listener

    @callback
    def set_audio_play_listener(
        self, audio_play_listener: Callable[[bytes], None]
    ) -> None:
        """Listen for WAV audio to play."""
        self._audio_play_listener = audio_play_listener

    @callback
    def set_tts_play_listener(self, tts_play_listener: Callable[[bytes], None]) -> None:
        """Listen for tts to play."""
        self._tts_play_listener = tts_play_listener

    @callback
    def add_system_stats_listener(
        self, system_stats_listener: Callable[[dict[str, Any]], None]
    ) -> None:
        """Add a listener for system stats updates."""
        self._system_stats_listener.append(system_stats_listener)

    @callback
    def remove_system_stats_listener(
        self, system_stats_listener: Callable[[dict[str, Any]], None]
    ) -> None:
        """Remove a listener for system stats updates."""
        self._system_stats_listener.remove(system_stats_listener)

    @callback
    def set_audio_settings_listener(
        self, audio_settings_listener: Callable[[], None]
    ) -> None:
        """Listen for updates to audio settings."""
        self._audio_settings_listener = audio_settings_listener

    def set_last_notification_listener(
        self, last_notification_listener: Callable[[str], None]
    ) -> None:
        """Add a listener for changes of last_notification."""
        self._last_notification_listener = last_notification_listener

    def get_assist_in_progress_entity_id(self, hass: HomeAssistant) -> str | None:
        """Return entity id for assist in progress binary sensor."""
        ent_reg = er.async_get(hass)
        return ent_reg.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{self.satellite_id}-assist_in_progress"
        )

    def get_muted_entity_id(self, hass: HomeAssistant) -> str | None:
        """Return entity id for satellite muted switch."""
        ent_reg = er.async_get(hass)
        return ent_reg.async_get_entity_id(
            "switch", DOMAIN, f"{self.satellite_id}-mute"
        )

    def get_pipeline_entity_id(self, hass: HomeAssistant) -> str | None:
        """Return entity id for pipeline select."""
        ent_reg = er.async_get(hass)
        return ent_reg.async_get_entity_id(
            "select", DOMAIN, f"{self.satellite_id}-pipeline"
        )

    def get_noise_suppression_level_entity_id(self, hass: HomeAssistant) -> str | None:
        """Return entity id for noise suppression select."""
        ent_reg = er.async_get(hass)
        return ent_reg.async_get_entity_id(
            "select", DOMAIN, f"{self.satellite_id}-noise_suppression_level"
        )

    def get_auto_gain_entity_id(self, hass: HomeAssistant) -> str | None:
        """Return entity id for auto gain amount."""
        ent_reg = er.async_get(hass)
        return ent_reg.async_get_entity_id(
            "number", DOMAIN, f"{self.satellite_id}-auto_gain"
        )

    def get_volume_multiplier_entity_id(self, hass: HomeAssistant) -> str | None:
        """Return entity id for microphone volume multiplier."""
        ent_reg = er.async_get(hass)
        return ent_reg.async_get_entity_id(
            "number", DOMAIN, f"{self.satellite_id}-volume_multiplier"
        )

    def get_vad_sensitivity_entity_id(self, hass: HomeAssistant) -> str | None:
        """Return entity id for VAD sensitivity."""
        ent_reg = er.async_get(hass)
        return ent_reg.async_get_entity_id(
            "select", DOMAIN, f"{self.satellite_id}-vad_sensitivity"
        )
