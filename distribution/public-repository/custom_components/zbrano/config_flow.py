from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import ZbranoApi, ZbranoApiError
from .const import CONF_TOKEN, CONF_URL, DEFAULT_URL, DOMAIN


class ZbranoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def _schema(self, user_input=None):
        return vol.Schema(
            {
                vol.Required(CONF_URL, default=(user_input or {}).get(CONF_URL, DEFAULT_URL)): str,
                vol.Required(CONF_TOKEN, default=(user_input or {}).get(CONF_TOKEN, "")): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )

    async def _validate(self, user_input):
        url = str(user_input[CONF_URL]).strip().rstrip("/")
        token = str(user_input[CONF_TOKEN]).strip()
        await ZbranoApi(async_get_clientsession(self.hass), url, token).health()
        return {CONF_URL: url, CONF_ACCESS_TOKEN: token}

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                data = await self._validate(user_input)
            except ZbranoApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="ZBRANO", data=data)
        return self.async_show_form(step_id="user", data_schema=self._schema(user_input), errors=errors)

    async def async_step_reconfigure(self, user_input=None):
        errors = {}
        entry = self._get_reconfigure_entry()
        defaults = {
            CONF_URL: entry.data.get(CONF_URL, DEFAULT_URL),
            CONF_TOKEN: "",
        }
        if user_input is not None:
            try:
                data = await self._validate(user_input)
            except ZbranoApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._schema(user_input or defaults),
            errors=errors,
        )
