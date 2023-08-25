"""Config flow for HomGar integration."""
from __future__ import annotations

import logging
from typing import Any

from homgarapi import HomgarApi, HomgarApiException
from homgarapi.devices import HomgarHome, HomgarHubDevice
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .api import AsyncHomgarApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def _check_api_get_homes(
    hass: HomeAssistant, username: str, password: str
) -> tuple[AsyncHomgarApi, list[HomgarHome]]:
    """Try to connect to Homgar and retrieve a list of homes.

    Returns API instance and list of homes.
    """

    api = AsyncHomgarApi(hass, HomgarApi({}))

    await api.ensure_logged_in(username, password)
    homes = await api.get_homes()

    return api, homes


async def _get_hubs_for_hid(api: AsyncHomgarApi, hid: str) -> list[HomgarHubDevice]:
    """Retrieve list of hubs for a particular home ID (hid)."""
    return await api.get_devices_for_hid(hid)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomGar."""

    VERSION = 1

    username: str | None = None
    password: str | None = None
    api: AsyncHomgarApi | None = None
    homes: list[HomgarHome] | None = None
    hid_hubs: list[HomgarHubDevice] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.username = user_input["username"]
            self.password = user_input["password"]
            if self.username is not None and self.password is not None:
                try:
                    api, homes = await _check_api_get_homes(
                        self.hass, self.username, self.password
                    )
                    self.api = api
                    self.homes = homes
                except HomgarApiException:
                    errors["base"] = "invalid_auth"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                else:
                    return self.async_show_form(
                        step_id="choose_home",
                        data_schema=vol.Schema(self.create_home_schema(homes)),
                    )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    def create_home_schema(self, homes: list[HomgarHome]):
        """Create schema for home selection step."""
        return {
            vol.Required("hid"): SelectSelector(
                config=SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=str(home.hid), label=home.name)
                        for home in homes
                    ],
                )
            )
        }

    async def async_step_choose_home(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step choosing which home to choose hubs from."""
        errors: dict[str, str] = {}
        if user_input is not None and user_input["hid"]:
            try:
                if self.api is None:
                    raise ValueError("API is None")
                self.hid_hubs = await _get_hubs_for_hid(self.api, user_input["hid"])
            except HomgarApiException:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                if not self.hid_hubs:
                    errors["base"] = "no_hubs"
                else:
                    return self.async_show_form(
                        step_id="choose_hub",
                        data_schema=vol.Schema(self.create_hub_schema(self.hid_hubs)),
                    )

        return self.async_show_form(
            step_id="choose_home",
            data_schema=vol.Schema(self.create_home_schema(self.homes or [])),
            errors=errors,
        )

    def create_hub_schema(self, hubs: list[HomgarHubDevice]):
        """Create schema for hub selection step."""
        return {
            vol.Required("mid"): SelectSelector(
                config=SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=str(hub.mid), label=hub.name)
                        for hub in hubs
                    ],
                )
            )
        }

    async def async_step_choose_hub(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step choosing which hub to use."""
        errors: dict[str, str] = {}
        if user_input is not None and user_input["mid"]:
            if not self.hid_hubs:
                raise ValueError("No hubs?")
            mid = int(user_input["mid"])
            return self.async_create_entry(
                title=next(hub for hub in self.hid_hubs if hub.mid == mid).name,
                data={"username": self.username, "password": self.password, "mid": mid},
            )

        return self.async_show_form(
            step_id="choose_hub",
            data_schema=vol.Schema(self.create_hub_schema(self.hid_hubs or [])),
            errors=errors,
        )
