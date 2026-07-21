from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientError
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MnemosClient
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_SSL,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .exceptions import MnemosAuthError, MnemosConnectionError
from .state import get_entry_state

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_USE_SSL, default=False): bool,
        vol.Required(CONF_API_KEY): str,
    }
)


async def _validate(hass, host: str, port: int, use_ssl: bool, api_key: str) -> dict[str, Any]:
    session = async_get_clientsession(hass)
    client = MnemosClient(session, host, port, api_key, use_ssl=use_ssl)
    return await client.healthz()


class MnemosConfigFlow(ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            use_ssl = bool(user_input.get(CONF_USE_SSL, False))
            api_key = user_input[CONF_API_KEY].strip()

            unique_id = f"{host}:{port}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                info = await _validate(self.hass, host, port, use_ssl, api_key)
            except MnemosAuthError:
                errors["base"] = "invalid_api_key"
            except MnemosConnectionError:
                errors["base"] = "cannot_connect"
            except ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during Mnemos config flow")
                errors["base"] = "unknown"
            else:
                title = f"Mnemos ({host}:{port})"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_USE_SSL: use_ssl,
                        CONF_API_KEY: api_key,
                    },
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                    description_placeholders={
                        "model": info.get("model") or "unknown",
                        "version": info.get("version") or "unknown",
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MnemosOptionsFlow(config_entry)


class MnemosOptionsFlow(OptionsFlow):

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            scan_interval = max(
                MIN_SCAN_INTERVAL,
                min(int(user_input[CONF_SCAN_INTERVAL]), MAX_SCAN_INTERVAL),
            )

            new_key = (user_input.get(CONF_API_KEY) or "").strip()
            current_key = self.entry.data.get(CONF_API_KEY, "")
            if new_key and new_key != current_key:
                try:
                    await _validate(
                        self.hass,
                        self.entry.data[CONF_HOST],
                        self.entry.data[CONF_PORT],
                        self.entry.data.get(CONF_USE_SSL, False),
                        new_key,
                    )
                except MnemosAuthError:
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._schema(show_key_value=new_key),
                        errors={CONF_API_KEY: "invalid_api_key"},
                    )
                except (MnemosConnectionError, ClientError):
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._schema(show_key_value=new_key),
                        errors={"base": "cannot_connect"},
                    )
                try:
                    state = get_entry_state(self.hass, self.entry.entry_id)
                    state.client.api_key = new_key
                except RuntimeError:
                    pass
                new_data = {**self.entry.data, CONF_API_KEY: new_key}
                self.hass.config_entries.async_update_entry(self.entry, data=new_data)

            return self.async_create_entry(
                title="",
                data={CONF_SCAN_INTERVAL: scan_interval},
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self._schema(),
        )

    def _schema(self, show_key_value: str | None = None) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Optional(
                    CONF_API_KEY,
                    default=(
                        show_key_value
                        if show_key_value is not None
                        else self.entry.data.get(CONF_API_KEY, "")
                    ),
                ): str,
            }
        )
