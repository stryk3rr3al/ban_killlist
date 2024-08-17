from __future__ import annotations

import logging
from ipaddress import IPv4Address, IPv6Address
from typing import List

import voluptuous as vol
from homeassistant.components.http.ban import KEY_BAN_MANAGER, IpBanManager
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("ip_addresses"): vol.All(cv.ensure_list, [cv.string]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Custom IP Ban from a config entry."""
    try:
        ban_manager: IpBanManager = hass.http.app[KEY_BAN_MANAGER]
    except KeyError:
        _LOGGER.warning(
            "Can't find ban manager. Custom IP Ban requires http.ip_ban_enabled to be True, so disabling."
        )
        return True

    _LOGGER.debug("Ban manager %s", ban_manager)
    
    # Define your list of IP addresses to ban
    banlist: List[str] = config.get(DOMAIN, {}).get("ip_addresses", [])
    if len(banlist) == 0:
        _LOGGER.info("No IPs provided to ban")
    else:
        _LOGGER.info("Custom banning IPs: %s", banlist)

        original_async_add_ban = IpBanManager.async_add_ban

        async def custom_async_add_ban(
            remote_addr: IPv4Address | IPv6Address,
        ) -> None:
            if str(remote_addr) in banlist:
                _LOGGER.info("Custom banning IP %s", remote_addr)
                await original_async_add_ban(ban_manager, remote_addr)
                
                # Perform additional actions here
                await send_ban_notifications(str(remote_addr))
            else:
                _LOGGER.info("IP %s is not in the banlist", remote_addr)

        # Override the original async_add_ban method
        ban_manager.async_add_ban = custom_async_add_ban

    return True

async def send_ban_notifications(ip_address: str) -> None:
    """Send notifications or perform actions when an IP is banned."""
    _LOGGER.info(f"Sending ban notification for IP: {ip_address}")

    # Example: Sending a curl request
    import asyncio
    import subprocess

    async def send_curl_request(url: str, data: str) -> None:
        command = [
            "curl", "-k", "-X", "POST",
            "-d", data,
            "-H", "Content-type: application/json",
            url
        ]
        process = await asyncio.create_subprocess_exec(*command)
        await process.wait()
        if process.returncode != 0:
            _LOGGER.error(f"Failed to execute curl command for IP {ip_address}")

    # URL for your API endpoint
    ban_url = "http://192.168.3.164:7775/ban"  # Change as needed
    kill_url = "http://192.168.3.164:7776/kill"  # Change as needed

    # Perform actions
    await asyncio.gather(
        send_curl_request(ban_url, f'{{"ban":"{ip_address}"}}'),
        send_curl_request(kill_url, f'{{"kill":"{ip_address}"}}')
    )
