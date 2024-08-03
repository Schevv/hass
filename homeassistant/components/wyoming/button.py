"""Wyoming button entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
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

    async_add_entities([
        WyomingSatelliteRingButton(item.satellite.device),
        WyomingSatelliteTestNotifyButton(item.satellite.device),
        WyomingSatelliteSpeakLastNotificationButton(item.satellite.device),
        ])


class WyomingSatelliteRingButton(
    WyomingSatelliteEntity, ButtonEntity
):
    """Entity to trigger a ringing sound on the satellite."""

    entity_description = ButtonEntityDescription(
        key="ring",
        translation_key="ring",
    )

    #current_sound = 0

    async def async_press(self) -> None:
        """Handle the button press."""
        self._device.play_ringtone(self.hass)

        #from . import sounds

        #soundlist = ['Air Plane Ding-SoundBible.com-496729130.wav', 'glass_ping-Go445-1207030150.wav', 'mixkit-happy-bells-notification-937.wav', 'mixkit-short-rooster-crowing-2470.wav', 'Music_Box-Big_Daddy-1389738694.wav', 'Simple-notification-sound.wav', 'sms-alert-1-daniel_simon.wav', 'sms-alert-2-daniel_simon.wav', 'sms-alert-3-daniel_simon.wav', 'sms-alert-4-daniel_simon.wav', 'sms-alert-5-daniel_simon.wav']

        #with importlib.resources.files(sounds).joinpath(soundlist[self.current_sound]).open('rb') as sound_data:
        #with importlib.resources.files().joinpath('test.wav').open('rb') as sound_data:
        #    buffered_sound_data = sound_data.read()
        #self.current_sound += 1
        #if self.current_sound >= len(soundlist):
        #    self.current_sound = 0
        #self._device.play_audio(buffered_sound_data)

class WyomingSatelliteTestNotifyButton(
    WyomingSatelliteEntity, ButtonEntity
):
    """Entity to trigger the notification sound on the satellite."""

    entity_description = ButtonEntityDescription(
        key="testnotificationsound",
        translation_key="testnotificationsound",
        entity_category=EntityCategory.DIAGNOSTIC
    )

    async def async_press(self) -> None:
        """Handle the button press."""
        self._device.play_notificationtone(self.hass)


class WyomingSatelliteSpeakLastNotificationButton(
    WyomingSatelliteEntity, ButtonEntity
):
    """Entity to speak out the last notification text on the satellite."""

    entity_description = ButtonEntityDescription(
        key="speak_last_notification",
        translation_key="speak_last_notification",
    )

    async def async_press(self) -> None:
        """Handle the button press."""
        if (message := self._device.last_notification) is not None:
            self._device.tts_play(message)
