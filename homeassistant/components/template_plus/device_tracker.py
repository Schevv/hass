from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .template_entity import TemplateEntity


class SwitchTemplate(TemplateEntity, TrackerEntity, RestoreEntity):
    def __init__(
        self, hass: HomeAssistant, config: dict[str, Any], unique_id: str | None
    ):
        super().__init__(hass, config=config, fallback_name=None, unique_id=unique_id)
