"""The udp integration."""
from __future__ import annotations
import socket

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.LIGHT]


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the REST command component."""

    def send_udp(service: ServiceCall):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        sock.sendto(
            bytes(service.data["message"], "utf-8"),
            (service.data["ip"], int(service.data["port"])),
        )

    hass.services.register(DOMAIN, "send", send_udp)
    return True


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Set up udp from a config entry."""

#     hass.data.setdefault(DOMAIN, {})
#     # TODO 1. Create API instance
#     # TODO 2. Validate the API connection (and authentication)
#     # TODO 3. Store an API object for your platforms to access
#     # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

#     await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

#     return True


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Unload a config entry."""
#     if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
#         hass.data[DOMAIN].pop(entry.entry_id)

#     return unload_ok
