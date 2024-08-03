from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    SwitchEntity,
)

from homeassistant.components.device_tracker import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
)
from homeassistant.components.device_tracker.config_entry import TrackerEntity

from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    CONF_SWITCHES,
    CONF_UNIQUE_ID,
    CONF_VALUE_TEMPLATE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.script import Script
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .template_entity import (
    TEMPLATE_ENTITY_COMMON_SCHEMA_LEGACY,
    TemplateEntity,
    rewrite_common_legacy_to_modern_conf,
)


class SwitchTemplate(TemplateEntity, TrackerEntity, RestoreEntity):
    def __init__(
        self, hass: HomeAssistant, config: dict[str, Any], unique_id: str | None
    ):
        super().__init__(hass, config=config, fallback_name=None, unique_id=unique_id)
