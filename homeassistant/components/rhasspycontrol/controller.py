"""Device Controller for Rhasspy"""

import asyncio
import functools
import importlib
import json
import logging
from typing import Any

import requests
import websockets

from homeassistant.components.select import SelectEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import now as dtnow

from . import sounds
from .const import DOMAIN, SOUNDS
from .rhasspy_status import RhasspyStatus

_LOGGER = logging.getLogger(__name__)


class RhasspyDeviceController(DataUpdateCoordinator[RhasspyStatus]):
    """Device controller for a single Rhasspy"""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, config_data) -> None:
        super().__init__(hass, _LOGGER, name="RhasspyControl")
        self.tts_notification_switch: SwitchEntity = None
        self.tts_notification_sound_switch: SwitchEntity = None
        self.ringer_sound: SelectEntity = None
        self.notification_sound: SelectEntity = None
        self.success_sound: SelectEntity = None
        self.hass = hass
        self.unique_id = entry.entry_id
        self.host = config_data["host"]
        self.port = config_data["port"]
        self.name = config_data["name"]
        self.site_id = "default"
        self.url = "http://" + self.host + ":" + str(self.port) + "/api/"
        self.ws_url = "ws://" + self.host + ":" + str(self.port) + "/api/"
        self.device = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Rhasspy Community",
            name=config_data["name"],
            sw_version=config_data["version"],
            configuration_url="http://" + self.host + ":" + str(self.port),
            model="Rhasspy",
        )
        self.current_task = None
        self.data = RhasspyStatus()
        self._mqtt_topics = {
            "hermes/hotword/toggleOn": self._hotword_toggle_on,
            "hermes/hotword/toggleOff": self._hotword_toggle_off,
            "rhasspy/audioServer/setVolume": self._set_volume,
            "hermes/asr/textCaptured": self._text_captured,
            "hermes/asr/startListening": self._start_listening_command,
            "hermes/asr/stopListening": self._stop_listening_command,
            f"hermes/audioServer/{self.site_id}/playFinished": self._play_finished,
            "hermes/error/audioServer/play": self._on_rhasspy_error,
            "hermes/error/audioServer/record": self._on_rhasspy_error,
            "hermes/error/asr": self._on_rhasspy_error,
            "hermes/error/dialogueManager": self._on_rhasspy_error,
            "rhasspy/error/g2p": self._on_rhasspy_error,
            "hermes/error/hotword": self._on_rhasspy_error,
            "hermes/error/nlu": self._on_rhasspy_error,
            "hermes/error/tts": self._on_rhasspy_error,
            "monitor/stats": self._on_stats,
        }
        entry.async_create_background_task(
            hass, self._async_mqtt_listen(), "MQTT Websocket Listener"
        )

    @property
    def selected_ringer_sound(self) -> str:
        """Returns the name of the currently selected ringer sound"""
        if self.ringer_sound is None:
            _LOGGER.warning("Ringer selector is None when needing sound")
            return list(SOUNDS.keys())[0]
        result = self.ringer_sound.current_option
        return result if result is not None else list(SOUNDS.keys())[0]

    @property
    def selected_notification_sound(self) -> str:
        """Returns the name of the currently selected notification sound"""
        if self.notification_sound is None:
            _LOGGER.warning("Notification sound selector is None when needing sound")
            return list(SOUNDS.keys())[0]
        result = self.notification_sound.current_option
        return result if result is not None else list(SOUNDS.keys())[0]

    @property
    def selected_success_sound(self) -> str:
        """Returns the name of the currently selected success sound"""
        if self.success_sound is None:
            _LOGGER.warning("Success sound selector is None when needing sound")
            return list(SOUNDS.keys())[0]
        result = self.success_sound.current_option
        return result if result is not None else list(SOUNDS.keys())[0]

    @property
    def tts_notifications(self) -> bool:
        """Are tts notifications currently enabled."""
        if self.tts_notification_switch is None:
            _LOGGER.warning("Tts selector is None when needing state")
            return False
        return self.tts_notification_switch.is_on

    @property
    def tts_notifications_as_sound(self) -> bool:
        """Are tts notifications to be played as sounds."""
        if self.tts_notification_sound_switch is None:
            _LOGGER.warning("Tts sound selector is None when needing state")
            return False
        return self.tts_notification_sound_switch.is_on

    async def perform_tts_notification(self, message: str, **kwargs: Any):
        """Checks if the endpoint covered by this controller should speak the given notification and sends the text if necessary"""
        if not self.tts_notifications:
            _LOGGER.debug("Notifications off on %s", self.name)
            return

        volume = kwargs.get("volume", None)
        if volume is not None:
            volume = int(volume)

        self.async_set_updated_data(
            self.data._replace(
                last_tts_notification=message,
                last_tts_notification_timestamp=dtnow(),
                last_tts_notification_title=kwargs.get("title", None),
            )
        )

        if self.tts_notifications_as_sound and not kwargs.get("force", False):
            self.play_sound(self.notification_sound.state)
            return

        await self.tts_speak(
            message,
            kwargs.get("voice", None),
            kwargs.get("language", None),
            kwargs.get("repeat", False) is True,
            volume,
            kwargs.get("siteid", None),
        )

    async def speak_last_notification(self) -> None:
        """Speak the last notification."""
        await self.perform_tts_notification(
            self.data.last_tts_notification,
            title=self.data.last_tts_notification_title,
            force=True,
        )

    def _hotword_toggle_on(self, payload):
        self.async_set_updated_data(self.data._replace(listening=True))

    def _hotword_toggle_off(self, payload):
        self.async_set_updated_data(self.data._replace(listening=False))

    def _set_volume(self, payload):
        volume = int(payload["volume"] * 100)
        self.async_set_updated_data(self.data._replace(volume=volume))

    def _on_rhasspy_error(self, payload):
        # Can't use fire_async since we're not on the event-loop
        self.hass.bus.fire(DOMAIN + "_error", payload)

    def _on_stats(self, payload) -> None:
        cpu_percentage = payload["cpu_percentage"]
        cpu_count = payload["cpu_count"]
        total_memory = payload["total_memory"]
        used_memory = payload["used_memory"]
        total_disk = payload["total_disk"]
        used_disk = payload["used_disk"]
        current_temp = payload["current_temp"]
        self.async_set_updated_data(
            self.data._replace(
                cpu_percentage=cpu_percentage,
                cpu_count=cpu_count,
                total_memory=total_memory,
                used_memory=used_memory,
                total_disk=total_disk,
                used_disk=used_disk,
                current_temp=current_temp,
            )
        )

    def _text_captured(self, payload):
        # session_id = payload.get("session_id", None)  # string or null
        # text = payload["text"]  # string
        # likelihood = payload["likelihood"]  # float
        # transcription_time = payload["seconds"]  # float
        # _LOGGER.warning("text_captured: %s %s %s", text, likelihood, transcription_time)
        # Can't use fire_async since we're not on the event-loop
        self.hass.bus.fire(DOMAIN + "_text_captured", payload)

    def _play_finished(self, payload):
        self.async_set_updated_data(self.data._replace(last_output_timestamp=dtnow()))
        # Can't use fire_async since we're not on the event-loop
        self.hass.bus.fire(DOMAIN + "_play_finished", payload)

    def _start_listening_command(self, payload):
        session_id = payload.get("session_id", None)  # string or null
        stopOnSilence = payload.get("stopOnSilence", None)  # bool
        wakeword = payload.get("wakewordId", None)  # string or null
        # Can't use fire_async since we're not on the event-loop
        self.hass.bus.fire(DOMAIN + "_start_listening_command", payload)

    def _stop_listening_command(self, payload):
        session_id = payload.get("session_id", None)  # string or null
        # Can't use fire_async since we're not on the event-loop
        self.async_set_updated_data(self.data._replace(last_input_timestamp=dtnow()))
        self.hass.bus.fire(DOMAIN + "_stop_listening_command", payload)

    async def _async_mqtt_listen(self) -> None:
        while True:
            try:
                _LOGGER.debug("Websocket connecting to %s", self.ws_url)
                async with websockets.connect(self.ws_url + "mqtt") as client:
                    self.async_set_updated_data(self.data._replace(available=True))
                    _LOGGER.debug("Websocket connected to %s", self.ws_url)
                    for topic in self._mqtt_topics:
                        await client.send(
                            '{ "type": "subscribe", "topic": "' + topic + '" }'
                        )

                    while True:
                        received_str = await client.recv()
                        _LOGGER.debug("Received: %s", received_str)
                        try:
                            received = json.loads(received_str)
                            topic = received["topic"]
                            payload = received.get("payload", None)
                            topic_handler = self._mqtt_topics.get(topic, None)
                            if topic_handler is not None:
                                payload["topic"] = topic
                                topic_handler(payload)
                            else:
                                _LOGGER.warning("Received unknown topic: %s", topic)

                        except asyncio.CancelledError:
                            raise
                        except BaseException as exc:
                            _LOGGER.error("Error: %s", exc, exc_info=exc)
            except asyncio.CancelledError:
                raise
            except BaseException as exc:
                _LOGGER.error("Error: %s", exc, exc_info=exc)
            self.async_set_updated_data(self.data._replace(available=False))
            await asyncio.sleep(
                60
            )  # On error wait 60 seconds before trying a reconnect

    async def async_post(self, endpoint: str, *args, **kwargs) -> None:
        """Sends a post request to the rhasspy endpoint"""
        _LOGGER.debug("posting to %s: %s %s", endpoint, args, kwargs)
        url = self.url + endpoint
        args = list(args)
        args.insert(0, url)

        return self.hass.async_add_executor_job(
            functools.partial(requests.post, *args, **kwargs)
        )

    async def _async_update_data(self) -> RhasspyStatus:
        return self.data

    async def async_set_volume(self, volume: int) -> None:
        """Sets the volume on Rhasspy"""
        await self.async_post("set-volume", data=str(volume / 100.0), timeout=1)

    async def play_sound(self, sound_filename: str) -> None:
        with importlib.resources.open_binary(sounds, sound_filename) as sound_data:
            buffered_sound_data = sound_data.read()
        await self.play_wav(buffered_sound_data)

    async def play_wav(self, wav_data: Any) -> None:
        await self.async_post(
            "play-wav", headers={"Content-Type": "audio/wav"}, data=wav_data
        )

    async def tts_speak(
        self,
        text: str,
        voice: str | None = None,
        language: str | None = None,
        repeat: bool | None = None,
        volume: int | None = None,
        siteid: str | None = None,
    ):
        """Speaks the given text on Rhasspy"""

        _LOGGER.warning(
            "Speaking: %s %s %s %s %s %s",
            text,
            voice,
            language,
            repeat,
            volume,
            siteid,
        )
        params = {}
        if voice is not None:
            params["voice"] = voice
        if language is not None:
            params["language"] = language
        if repeat:
            params["repeat"] = "true"
        if volume is not None:
            params["volume"] = float(volume) / 100.0
        if siteid is not None:
            params["siteid"] = siteid

        await self.async_post(
            "text-to-speech", params=params, data=text.encode("utf-8")
        )
