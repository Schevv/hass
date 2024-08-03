"""Provides device actions for Rhasspy Control."""
from __future__ import annotations
import logging

import voluptuous as vol

from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_TYPE,
)
from homeassistant.components.button import SERVICE_PRESS

from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.typing import ConfigType, TemplateVarsType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

ACTION_TYPES = {"ring"}

ACTION_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ACTION_TYPES),
        vol.Required(CONF_ENTITY_ID): cv.entity_domain(DOMAIN),
    }
)


async def async_get_actions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device actions for Rhasspy Control devices."""
    _LOGGER.warning("async_get_actions")
    registry = er.async_get(hass)
    actions = []

    # TODO Read this comment and remove it.
    # This example shows how to iterate over the entities of this device
    # that match this integration. If your actions instead rely on
    # calling services, do something like:
    # zha_device = await _async_get_zha_device(hass, device_id)
    # return zha_device.device_actions

    # Get all the integrations entities for this device
    for entry in er.async_entries_for_device(registry, device_id):
        _LOGGER.warning("async_get_actions: %s %s", entry.name, entry.entity_id)
        if entry.domain != DOMAIN:
            continue
        if entry.name != "Ring":
            continue

        # Add actions for each entity that belongs to this integration
        # TODO add your own actions.
        base_action = {
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_ENTITY_ID: entry.entity_id,
        }

        actions.append({**base_action, CONF_TYPE: "ring"})

    return actions


async def async_call_action_from_config(
    hass: HomeAssistant,
    config: ConfigType,
    variables: TemplateVarsType,
    context: Context | None,
) -> None:
    """Execute a device action."""
    service_data = {ATTR_ENTITY_ID: config[CONF_ENTITY_ID]}

    # if config[CONF_TYPE] == "turn_on":
    #    service = SERVICE_TURN_ON
    # elif config[CONF_TYPE] == "turn_off":
    #    service = SERVICE_TURN_OFF

    await hass.services.async_call(
        DOMAIN, SERVICE_PRESS, service_data, blocking=True, context=context
    )
