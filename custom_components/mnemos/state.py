from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .api import MnemosClient
from .coordinator import MnemosCoordinator


@dataclass
class MnemosEntryState:
    client: MnemosClient
    coordinator: MnemosCoordinator
    last_identify: dict[str, Any] | None = None
    last_identify_listeners: set[Callable[[], None]] = field(default_factory=set)

    def set_last_identify(self, payload: dict[str, Any]) -> None:
        self.last_identify = payload
        for cb in list(self.last_identify_listeners):
            try:
                cb()
            except Exception:  # noqa: BLE001
                pass


def get_entry_state(hass, entry_id: str) -> MnemosEntryState:
    bucket = hass.data.setdefault("mnemos", {}).get(entry_id)
    if not isinstance(bucket, MnemosEntryState):
        raise RuntimeError(f"Mnemos entry {entry_id} is not initialised")
    return bucket


def list_entry_states(hass) -> list[MnemosEntryState]:
    out: list[MnemosEntryState] = []
    for v in (hass.data.get("mnemos") or {}).values():
        if isinstance(v, MnemosEntryState):
            out.append(v)
    return out


def resolve_entry_state(hass) -> MnemosEntryState:
    states = list_entry_states(hass)
    if not states:
        from homeassistant.exceptions import HomeAssistantError 

        raise HomeAssistantError("Mnemos is not configured")
    if len(states) > 1:
        from homeassistant.exceptions import HomeAssistantError

        names = ", ".join(s.client.base_url for s in states)
        raise HomeAssistantError(
            f"Multiple Mnemos entries configured ({names}); this build of "
            "mnemos.identify only supports a single backend. File an issue."
        )
    return states[0]
