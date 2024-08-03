"""Config flow for GarbageCalendar integration."""
from __future__ import annotations

import logging

from homeassistant import config_entries

# from homeassistant.exceptions import HomeAssistantError
from homeassistant.components import onboarding

# from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

# from typing import Any

# import voluptuous as vol


_LOGGER = logging.getLogger(__name__)


class DiscoveryFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a discovery config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the discovery config flow."""
        self._domain = DOMAIN
        self._title = "Müllkalender"

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        await self.async_set_unique_id(self._domain, raise_on_progress=False)

        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None) -> FlowResult:
        """Confirm setup."""
        if user_input is None and onboarding.async_is_onboarded(self.hass):
            self._set_confirm_only()
            return self.async_show_form(step_id="confirm")

        if self.source == config_entries.SOURCE_USER:
            # Get current discovered entries.
            in_progress = self._async_in_progress()

            if not (has_devices := bool(in_progress)):
                has_devices = True

            if not has_devices:
                return self.async_abort(reason="no_devices_found")

            # Cancel the discovered one.
            for flow in in_progress:
                self.hass.config_entries.flow.async_abort(flow["flow_id"])

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title=self._title, data={})


# TODO adjust the data schema to the data that you need
# STEP_USER_DATA_SCHEMA = vol.Schema(
#    {
#        vol.Required("host"): str,
#        vol.Required("username"): str,
#        vol.Required("password"): str,
#    }
# )


# class PlaceholderHub:
#    """Placeholder class to make tests pass.
#
#    TODO Remove this placeholder class and replace with things from your PyPI package.
#    """
#
#    def __init__(self, host: str) -> None:
#        """Initialize."""
#        self.host = host
#
#    async def authenticate(self, username: str, password: str) -> bool:
#        """Test if we can authenticate with the host."""
#        return True


# async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
#     """Validate the user input allows us to connect.

#     Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
#     """
#     # TODO validate the data can be used to set up a connection.

#     # If your PyPI package is not built with async, pass your methods
#     # to the executor:
#     # await hass.async_add_executor_job(
#     #     your_validate_func, data["username"], data["password"]
#     # )

#     hub = PlaceholderHub(data["host"])

#     if not await hub.authenticate(data["username"], data["password"]):
#         raise InvalidAuth

#     # If you cannot connect:
#     # throw CannotConnect
#     # If the authentication is wrong:
#     # InvalidAuth

#     # Return info that you want to store in the config entry.
#     return {"title": "Name of the device"}


# class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
#     """Handle a config flow for GarbageCalendar."""

#     VERSION = 1

#     async def async_step_user(
#         self, user_input: dict[str, Any] | None = None
#     ) -> FlowResult:
#         """Handle the initial step."""
#         if user_input is None:
#             return self.async_show_form(
#                 step_id="user", data_schema=STEP_USER_DATA_SCHEMA
#             )

#         errors = {}

#         try:
#             info = await validate_input(self.hass, user_input)
#         except CannotConnect:
#             errors["base"] = "cannot_connect"
#         except InvalidAuth:
#             errors["base"] = "invalid_auth"
#         except Exception:  # pylint: disable=broad-except
#             _LOGGER.exception("Unexpected exception")
#             errors["base"] = "unknown"
#         else:
#             return self.async_create_entry(title=info["title"], data=user_input)

#         return self.async_show_form(
#             step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
#         )


# class CannotConnect(HomeAssistantError):
#     """Error to indicate we cannot connect."""


# class InvalidAuth(HomeAssistantError):
#     """Error to indicate there is invalid auth."""
