from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, SOUNDS
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
            RhasspyBaseSoundSelectorEntity(controller, "Ringer Sound", "mdi:bell-cog"),
            RhasspyBaseSoundSelectorEntity(
                controller, "Notification Sound", "mdi:message-cog-outline"
            ),
            RhasspyBaseSoundSelectorEntity(
                controller, "Success Sound", "mdi:check-circle"
            ),
        ],
        True,
    )


class RhasspyBaseSoundSelectorEntity(SelectEntity, RestoreEntity):
    """Base class for entities to select a sound."""

    def __init__(
        self, device_controller: RhasspyDeviceController, name: str, icon: str
    ) -> None:
        self.device_controller = device_controller
        self._attr_device_info = device_controller.device
        self._basic_name = name
        self._attr_assumed_state = False
        self._attr_has_entity_name = True
        self._attr_icon = icon
        self._attr_should_poll = False
        self._attr_unique_id = (
            device_controller.unique_id + "-" + name.lower().replace(" ", "-")
        )
        self._attr_name = name
        self._attr_options = list(SOUNDS.keys())
        self._attr_current_option = self._attr_options[0]
        self._attr_available = True
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_select_option(self, option: str) -> None:
        """Updates the current value."""
        self._attr_current_option = option
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state in self.options:
            self._attr_current_option = state.state
        setattr(
            self.device_controller, self._basic_name.lower().replace(" ", "_"), self
        )


class RhasspyDefaultSoundSelectorEntity(RhasspyBaseSoundSelectorEntity):
    """Selects the default notification sound"""

    def __init__(self, device_controller: RhasspyDeviceController) -> None:
        super().__init__(device_controller, "Ringer Sound", "mdi:bell-cog")
