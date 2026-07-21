from __future__ import annotations

from datetime import timezone
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_API_KEY,
    DATA_HEALTH,
    DATA_MODEL,
)
from .state import get_entry_state

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    state = get_entry_state(hass, entry.entry_id)
    coordinator = state.coordinator
    data = coordinator.data or {}
    last_success = coordinator.last_success
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_success": (
                last_success.replace(tzinfo=timezone.utc).isoformat()
                if last_success
                else None
            ),
            "last_error": coordinator.last_error,
        },
        "backend": {
            "health": data.get(DATA_HEALTH),
            "model": data.get(DATA_MODEL),
        },
        "last_identify": state.last_identify,
    }
