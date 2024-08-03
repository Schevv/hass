from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .protocol import Inputs

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iRobot Roomba vacuum cleaner."""
    coordinators = hass.data[DOMAIN][config_entry.entry_id].values()
    async_add_entities(
        [SdcpInputSelectEntity(coordinator) for coordinator in coordinators], True
    )


class SdcpInputSelectEntity(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device
        self._attr_unique_id = (
            str(coordinator.projector.info.serial_number) + "sdcp-input"
        )
        self._attr_has_entity_name = True
        self._attr_name = "Input"
        self._attr_options = [input.name for input in Inputs]
        self._attr_current_option = Inputs(0).name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_current_option = self.coordinator.input
        self.async_write_ha_state()

    def select_option(self, option: str) -> None:
        input_enum = next((input for input in Inputs if input.name == option), None)
        self.coordinator.project.set_input(input_enum)
