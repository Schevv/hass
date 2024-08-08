"""The listservice integration."""

from __future__ import annotations

import json
import logging

# from homeassistant.util.async_ import run_callback_threadsafe
import voluptuous as vol

from homeassistant.config_entries import ConfigType
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CALL_SCHEMA = vol.Schema(
    {
        vol.Required("service"): cv.string,
        vol.Optional("data"): dict,
        vol.Optional("target"): cv.TARGET_SERVICE_FIELDS,
        vol.Optional("transforms"): dict,
    }
)


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up is called when Home Assistant is loading our component."""

    async def handle_call(call: ServiceCall):
        """Handle the service call."""

        service = call.data.get("service", None)
        service_parts = str(service).split(".", 1)
        if len(service_parts) == 1:
            raise ValueError("service must be domain.service_name")
        domain = service_parts[0]
        service = service_parts[1]

        data = dict(call.data.get("data", {}))
        for k, v in dict(call.data.get("transforms", {})).items():
            key_segments = k.split(".")

            to_transform = data
            for segment in key_segments:
                if segment not in to_transform:
                    raise ValueError("Cannot transform missing key: " + k)
                to_transform = to_transform[segment]
            if v == "list":
                result = [s.strip() for s in str(to_transform).split(",")]
            elif v == "striplist":
                result = [
                    s for s in (s.strip() for s in str(to_transform).split(",")) if s
                ]
            elif v == "intlist":
                result = [
                    int(s)
                    for s in (s.strip() for s in str(to_transform).split(","))
                    if s
                ]
            elif v == "dict":
                result = dict(
                    (k.strip(), v.strip())
                    for (k, v) in (
                        i.split(":", 1) for i in str(to_transform).split(",")
                    )
                )
            elif v == "json":
                result = json.loads(str(to_transform))
            else:
                raise ValueError('Wrong type of conversion: "' + v + '" on "' + k + '"')
            to_transform = data
            for segment in key_segments[:-1]:
                to_transform = to_transform[segment]
            to_transform[key_segments[-1]] = result

        service_obj = hass.services.async_services().get(domain, {}).get(service, None)
        if service_obj is None:
            raise ValueError("Unkown service: " + domain + "." + service)

        return_response = service_obj.supports_response != SupportsResponse.NONE

        _LOGGER.debug(
            "Calling service %s.%s with data: %s (Response: %s)",
            domain,
            service,
            data,
            return_response,
        )
        result = await hass.services.async_call(
            domain,
            service,
            service_data=data,
            blocking=True,
            context=call.context,
            target=call.data.get("target", None),
            return_response=return_response,
        )

        if result is not None:
            return result

    hass.services.register(
        DOMAIN, "call", handle_call, CALL_SCHEMA, SupportsResponse.OPTIONAL
    )
    # run_callback_threadsafe(
    #    hass.loop, hass.services.async_register, DOMAIN, "call", handle_call, CALL_SCHEMA, SupportsResponse.OPTIONAL
    # ).result()

    # Return boolean to indicate that initialization was successful.
    return True
