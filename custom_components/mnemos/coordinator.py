from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MnemosClient
from .const import (
    CONF_SCAN_INTERVAL,
    DATA_HEALTH,
    DATA_MODEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .exceptions import (
    MnemosApiError,
    MnemosAuthError,
    MnemosConnectionError,
)

_LOGGER = logging.getLogger(__name__)


class MnemosCoordinator(DataUpdateCoordinator[dict[str, Any]]):

    def __init__(
        self,
        hass: HomeAssistant,
        client: MnemosClient,
        scan_interval: int,
    ) -> None:
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._last_success: datetime | None = None
        self._last_error: str | None = None

    @property
    def last_success(self) -> datetime | None:
        return self._last_success

    @property
    def last_error(self) -> str | None:
        return self._last_error

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            health, model = await asyncio.gather(
                self.client.healthz(),
                self.client.model_info(),
            )
        except MnemosAuthError as err:
            self._last_error = f"auth: {err}"
            raise UpdateFailed(str(err)) from err
        except (MnemosConnectionError, MnemosApiError, ClientError) as err:
            self._last_error = str(err)
            raise UpdateFailed(str(err)) from err
        except Exception as err:  # noqa: BLE001
            self._last_error = str(err)
            raise UpdateFailed(str(err)) from err

        self._last_success = datetime.utcnow()
        self._last_error = None
        return {DATA_HEALTH: health, DATA_MODEL: model}


def get_coordinator(hass: HomeAssistant, entry: ConfigEntry):
    from .state import get_entry_state

    return get_entry_state(hass, entry.entry_id).coordinator
