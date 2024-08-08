import logging

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA

# from homeassistant.components.homeassistant.triggers.state import TRIGGER_STATE_SCHEMA
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, Event, HassJob, HomeAssistant, callback
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TRIGGER_TYPES = {
    "text_captured",
    "play_finished",
    "start_listening_command",
    "stop_listening_command",
}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device triggers for Rhasspy devices."""
    # registry = er.async_get(hass)

    return [
        {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: type,
        }
        for type in TRIGGER_TYPES
    ]


async def async_attach_trigger(hass, config, action, trigger_info):
    """Attach a trigger."""
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: "mydomain_event",
            event_trigger.CONF_EVENT_DATA: {
                CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                CONF_TYPE: config[CONF_TYPE],
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    trigger_data = trigger_info["trigger_data"]
    job = HassJob(action)

    if config[CONF_TYPE] == "turn_on":
        entity_id = config[CONF_ENTITY_ID]

        @callback
        def _handle_event(event: Event) -> None:
            if event.data[ATTR_ENTITY_ID] == entity_id:
                hass.async_run_hass_job(
                    job,
                    {
                        "trigger": {
                            **trigger_data,  # type: ignore[arg-type]  # https://github.com/python/mypy/issues/9117
                            **config,
                            "description": f"{DOMAIN} - {entity_id}",
                        }
                    },
                    event.context,
                )

        return hass.bus.async_listen(EVENT_TURN_ON, _handle_event)

    return lambda: None
