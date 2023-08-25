"""Async wrapper for homgarapi package."""

from homgarapi import HomgarApi
from homgarapi.devices import HomgarHome, HomgarHubDevice

from homeassistant.core import HomeAssistant


class AsyncHomgarApi:
    """Async wrapper for HomgarApi."""

    def __init__(self, hass: HomeAssistant, api: HomgarApi) -> None:
        """Instantiate the wrapper. Uses the hass instance for async execution of homgarapi sync methods."""
        self.api = api
        self.hass = hass

    async def ensure_logged_in(self, username: str, password: str) -> None:
        """Try to log in. Throws HomgarApiException on failure."""
        return await self.hass.async_add_executor_job(
            self.api.ensure_logged_in, username, password
        )

    async def get_homes(self) -> list[HomgarHome]:
        """Retrieve available homes for the current user."""
        return await self.hass.async_add_executor_job(self.api.get_homes)

    async def get_devices_for_hid(self, hid: str) -> list[HomgarHubDevice]:
        """Retrieve available devices (hubs) for the given home id."""
        return await self.hass.async_add_executor_job(self.api.get_devices_for_hid, hid)

    async def get_device_status(self, hub: HomgarHubDevice) -> None:
        """Update the given hub and its subdevices with the current status and sensor values."""
        return await self.hass.async_add_executor_job(self.api.get_device_status, hub)
