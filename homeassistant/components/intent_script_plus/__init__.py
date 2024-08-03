"""Handle intents with scripts."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.const import CONF_TYPE, SERVICE_RELOAD
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import (
    config_validation as cv,
    intent,
    service,
    template,
    entity_registry,
    device_registry,
)
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN
from .observable_script import ObservableScript

_LOGGER = logging.getLogger(__name__)

CONF_USERS = "users"
CONF_SCRIPTS = "scripts"

CONF_INTENTS = "intents"
CONF_SPEECH = "speech"
CONF_REPROMPT = "reprompt"

CONF_ACTION = "action"
CONF_CARD = "card"
CONF_TITLE = "title"
CONF_CONTENT = "content"
CONF_TEXT = "text"
CONF_ASYNC_ACTION = "async_action"

DATA_SESSION_DATA = "session_data"
DATA_SESSION_PERSISTENT = "persistent_data"
DATA_SESSION_SPEECH = "speech"
DATA_SESSION_SUCCESS = "success"
DATA_INTENTS = "intents"
DATA_USERS = "users"
DATA_USER_ENTITY = "entity_id"
DATA_USER_HISTORY = "history"
DATA_USER_UNDO = "undo"
DATA_HISTORY = "history"
DATA_SESSION = "session"

RESPONSE_VARIABLE_SPEECH = "SPEECH"
RESPONSE_VARIABLE_SESSION_DATA = "SESSION_DATA"
RESPONSE_VARIABLE_ACK_SOUND = "ACKNOWLEDGEMENT"
RESPONSE_VARIABLE_PERSISTENT_DATA = "PERSISTENT_DATA"
RESPONSE_VARIABLE_UNDO_INTEND = "UNDO_INTENT"
RESPONSE_VARIABLE_UNDO_SLOTS = "UNDO_SLOTS"

DEFAULT_CONF_ASYNC_ACTION = False

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            vol.Optional(CONF_USERS): {cv.string: cv.string},
            vol.Optional(CONF_SCRIPTS): {
                cv.string: {
                    vol.Optional(CONF_ACTION): cv.SCRIPT_SCHEMA,
                    vol.Optional(
                        CONF_ASYNC_ACTION, default=DEFAULT_CONF_ASYNC_ACTION
                    ): cv.boolean,
                    vol.Optional(CONF_CARD): {
                        vol.Optional(CONF_TYPE, default="simple"): cv.string,
                        vol.Required(CONF_TITLE): cv.template,
                        vol.Required(CONF_CONTENT): cv.template,
                    },
                    vol.Optional(CONF_SPEECH): {
                        vol.Optional(CONF_TYPE, default="plain"): cv.string,
                        vol.Required(CONF_TEXT): cv.template,
                    },
                    vol.Optional(CONF_REPROMPT): {
                        vol.Optional(CONF_TYPE, default="plain"): cv.string,
                        vol.Required(CONF_TEXT): cv.template,
                    },
                }
            },
        }
    },
    extra=vol.ALLOW_EXTRA,
)

history_length = 5

async def async_reload(hass: HomeAssistant, servie_call: ServiceCall) -> None:
    """Handle start Intent Script service call."""
    new_config = await async_integration_yaml_config(hass, DOMAIN)
    existing_intents = hass.data[DOMAIN].get(DATA_INTENTS, [])

    for intent_type in existing_intents:
        intent.async_remove(hass, intent_type)

    if not new_config or DOMAIN not in new_config:
        hass.data[DOMAIN][DATA_INTENTS] = {}
        hass.data[DOMAIN][DATA_USERS] = {}
        # HISTORY VON INTENTS ERSTELLEN
        # DIREKTE ABHÄNGIGKEIT VON RHASSPY_CONTROL?
        # UNDO
        return

    async_load_intent_config(hass, new_config[DOMAIN])


def async_load_intent_config(hass: HomeAssistant, config: dict):
    """Load YAML intents into the intent system."""
    users = config.get(CONF_USERS, {})
    intents = config.get(CONF_SCRIPTS, {})
    template.attach(hass, intents)
    hass.data[DOMAIN][DATA_INTENTS] = intents
    for user_id, entity in dict(users).items():
        hass.data[DOMAIN][DATA_USERS][user_id] = { DATA_USER_HISTORY: [], DATA_USER_UNDO: [], DATA_USER_ENTITY: entity }

    for intent_type, conf in intents.items():
        if CONF_ACTION in conf:
            conf[CONF_ACTION] = ObservableScript(
                hass,
                conf[CONF_ACTION],
                f"Intent Script {intent_type}",
                DOMAIN,
            )
        intent.async_register(hass, ScriptIntentHandler(intent_type, conf))


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the intent script component."""

    hass.data.setdefault(DOMAIN, {}).setdefault(DATA_HISTORY, {})
    hass.data[DOMAIN].setdefault(DATA_SESSION, {})
    hass.data[DOMAIN].setdefault(DATA_SESSION_PERSISTENT, {})

    async def async_service_response(service_call: ServiceCall) -> None:
        speech = service_call.data.get(DATA_SESSION_SPEECH, None)
        session_data = service_call.data.get(DATA_SESSION_DATA, None)
        success = service_call.data.get(DATA_SESSION_SUCCESS, None)
        hass.data[DOMAIN][DATA_SESSION][service_call.context.user_id] = {
            DATA_SESSION_SPEECH: speech,
            DATA_SESSION_SUCCESS: success,
            DATA_SESSION_DATA: session_data,
        }

    async_load_intent_config(hass, config[DOMAIN])

    async def _handle_reload(servie_call: ServiceCall) -> None:
        return await async_reload(hass, servie_call)

    service.async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
    )

    hass.services.async_register(DOMAIN, "response", async_service_response)

    return True


class ScriptIntentHandler(intent.IntentHandler):
    """Respond to an intent with a script."""

    def __init__(self, intent_type, config) -> None:
        """Initialize the script intent handler."""
        self.intent_type = intent_type
        self.config = config

    async def _call_script_shielded(self, action, variables, context) -> None:
        try:
            await action.async_run(variables, context)
        except:  # pylint: disable=W0702
            pass

    async def async_handle(self, intent_obj: intent.Intent):
        """Handle the intent."""
        speech = self.config.get(CONF_SPEECH)
        reprompt = self.config.get(CONF_REPROMPT)
        card = self.config.get(CONF_CARD)
        action = self.config.get(CONF_ACTION)
        is_async_action = self.config.get(CONF_ASYNC_ACTION)
        slots = {key: value["value"] for key, value in intent_obj.slots.items()}
        hass = intent_obj.hass
        user_id = intent_obj.context.user_id
        user_data = hass.data[DOMAIN][DATA_USERS].get(user_id, {})
        target_entity_id = user_data.get(DATA_USER_ENTITY, None)
        if target_entity_id is not None:
            er = entity_registry.async_get(hass)
            entity = er.async_get(target_entity_id)
            device_id = entity.device_id
            area_id = entity.area_id
            if area_id is None and device_id is not None:
                dr = device_registry.async_get(hass)
                device = dr.async_get(device_id)
                area_id = device.area_id
        else:
            area_id = None
            device_id = None

        slots["AREA"] = area_id
        slots["TARGET_ENTITY"] = target_entity_id
        slots["DEVICE"] = device_id
        slots[RESPONSE_VARIABLE_PERSISTENT_DATA] = hass.data[DOMAIN][
            DATA_SESSION_PERSISTENT
        ].get(user_id, {})

        # domain_data = intent_obj.hass.data[DOMAIN]
        # session_data = {}
        # if user_id in domain_data:
        #    session_data = domain_data[user_id].get(DATA_SESSION_DATA, {})
        #    del domain_data[user_id]
        session_data = hass.data[DOMAIN][DATA_SESSION].get(user_id, {})

        _LOGGER.debug(
            "Intent named %s received with slots: %s and data %s",
            intent_obj.intent_type,
            {
                key: value
                for key, value in slots.items()
                if not key.startswith("_") and not key.endswith("_raw_value")
            },
            session_data,
        )

        variables = slots | session_data

        if action is not None:
            if is_async_action:
                hass.async_create_task(
                    self._call_script_shielded(action, variables, intent_obj.context)
                )
            else:
                try:
                    script_run = await action.async_run(variables, intent_obj.context)
                    variables = script_run._variables  # pylint: disable=W0212
                except:  # pylint: disable=W0702
                    pass

        response = intent_obj.create_response()

        if RESPONSE_VARIABLE_SPEECH in variables:
            response.async_set_speech(variables[RESPONSE_VARIABLE_SPEECH])
        elif speech is not None:
            response.async_set_speech(
                speech[CONF_TEXT].async_render(slots, parse_result=False),
                speech[CONF_TYPE],
            )
        # elif not is_async_action and user_id in domain_data:
        #    speech_from_service = domain_data[user_id].get(DATA_SESSION_SPEECH, None)
        #    if speech_from_service:
        #        del domain_data[user_id][DATA_SESSION_SPEECH]
        #        response.async_set_speech(speech_from_service)

        if RESPONSE_VARIABLE_SESSION_DATA in variables:
            hass.data[DOMAIN][DATA_SESSION][user_id] = variables[
                RESPONSE_VARIABLE_SESSION_DATA
            ]
        elif user_id in hass.data[DOMAIN][DATA_SESSION]:
            del hass.data[DOMAIN][DATA_SESSION][user_id]

        if reprompt is not None:
            text_reprompt = reprompt[CONF_TEXT].async_render(slots, parse_result=False)
            if text_reprompt:
                response.async_set_reprompt(
                    text_reprompt,
                    reprompt[CONF_TYPE],
                )

        if card is not None:
            response.async_set_card(
                card[CONF_TITLE].async_render(slots, parse_result=False),
                card[CONF_CONTENT].async_render(slots, parse_result=False),
                card[CONF_TYPE],
            )

        hass.data[DOMAIN][DATA_SESSION_PERSISTENT][user_id] = variables.get(
            RESPONSE_VARIABLE_PERSISTENT_DATA, {}
        )

        if variables.get(RESPONSE_VARIABLE_ACK_SOUND, False):
            if target_entity_id is None:
                _LOGGER.warning("Cannot find entity_id for user %s", user_id)
            else:
                await hass.services.async_call(
                    "rhasspycontrol",
                    "play_sound",
                    {"entity_id": target_entity_id, "sound": "SUCCESS"},
                    blocking=True,
                    context=intent_obj.context,
                )

        if variables.get()

        return response
