"""Config flow for Rhasspy Control integration."""

from __future__ import annotations

import logging
from typing import Any

# from requests import request
import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            "name",
            "Name of the Rhasspy Device in Home Assistant",
            description="Name Desc",
        ): str,
        vol.Required("host", "Hostname or IP of Rhasspy"): str,
        vol.Required("port", "Port of Rhasspy Webserver", 12101): int,
    }
)


def read_profile(data: dict[str, Any]):
    result = requests.get(
        "http://" + data["host"] + ":" + str(data["port"]) + "/api/profile",
        timeout=2,
    ).json()
    result["version"] = requests.get(
        "http://" + data["host"] + ":" + str(data["port"]) + "/api/version",
        timeout=2,
    ).content.decode()
    return result


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        profile = await hass.async_add_executor_job(read_profile, data)
        return {
            "name": data["name"],
            "host": data["host"],
            "port": data["port"],
            "version": profile["version"],
            "profile": profile["name"],
        }
    except Exception as exc:
        _LOGGER.warning(
            "Cannot connect to %s, %s", data["host"], data["port"], exc_info=exc
        )
        raise CannotConnect(exc) from exc

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    # hub = PlaceholderHub(data["host"])

    # if not await hub.authenticate(data["username"], data["password"]):
    #    raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": data["name"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rhasspy Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["name"], data=info)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
