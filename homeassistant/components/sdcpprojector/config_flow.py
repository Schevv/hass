"""Config flow for Sony Projector."""
# from typing import Any, Awaitable, Union

from homeassistant import config_entries
from homeassistant.components import onboarding
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .pysdcp import ProjectorInfo, async_find_projector


async def async_find_devices(hass: HomeAssistant) -> list[ProjectorInfo]:
    """Return if there are devices that can be discovered."""
    # devices = await hass.async_add_executor_job(async_find_projector)
    devices = await hass.async_add_job(async_find_projector)
    return devices


class DiscoveryFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a discovery config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the discovery config flow."""
        self._domain = DOMAIN
        self._title = "Sony Projector"
        # self._discovery_function = discovery_function

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
                devices = await self.hass.async_add_job(async_find_devices, self.hass)
                has_devices = len(devices) > 0

            if not has_devices:
                return self.async_abort(reason="no_devices_found")

            # Cancel the discovered one.
            for flow in in_progress:
                self.hass.config_entries.flow.async_abort(flow["flow_id"])

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title=self._title, data={"devices": devices})
