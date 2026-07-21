from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CONFIDENCE,
    ATTR_NAME,
    ATTR_PERSONS,
    ATTR_TOOK_MS,
    ATTR_UNKNOWN,
    DATA_HEALTH,
    DATA_MODEL,
    DOMAIN,
    HEALTH_KEY_MODEL,
    HEALTH_KEY_MODEL_LOADED,
    HEALTH_KEY_REINDEX_DONE,
    HEALTH_KEY_REINDEX_IN_PROGRESS,
    HEALTH_KEY_REINDEX_TOTAL,
    HEALTH_KEY_STATUS,
    HEALTH_KEY_VERSION,
    MANUFACTURER,
    MODEL_NAME,
)
from .coordinator import MnemosCoordinator
from .state import get_entry_state


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    state = get_entry_state(hass, entry.entry_id)
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    async_add_entities(
        [
            MnemosModelSensor(state.coordinator, host, port, entry),
            MnemosLastIdentifySensor(hass, entry, host, port),
            MnemosStatusSensor(state.coordinator, host, port, entry),
            MnemosVersionSensor(state.coordinator, host, port, entry),
            MnemosModelLoadedSensor(state.coordinator, host, port, entry),
        ]
    )


class MnemosModelSensor(CoordinatorEntity[MnemosCoordinator], SensorEntity):

    _attr_has_entity_name = True
    _attr_name = "Model"
    _attr_icon = "mdi:brain"
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: MnemosCoordinator,
        host: str,
        port: int,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_model"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL_NAME,
            name=f"Mnemos ({host}:{port})",
        )

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        health = self.coordinator.data.get(DATA_HEALTH) or {}
        return health.get(HEALTH_KEY_MODEL)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {
                "embedding_dim": None,
                "det_size": None,
                "reindex_in_progress": None,
                "reindex_done": None,
                "reindex_total": None,
                "reindex_percent": None,
            }
        model = self.coordinator.data.get(DATA_MODEL) or {}
        health = self.coordinator.data.get(DATA_HEALTH) or {}
        in_progress = bool(
            health.get(HEALTH_KEY_REINDEX_IN_PROGRESS)
            or model.get("reindex_in_progress")
        )
        total = int(
            health.get(HEALTH_KEY_REINDEX_TOTAL) or model.get("reindex_total") or 0
        )
        done = int(
            health.get(HEALTH_KEY_REINDEX_DONE) or model.get("reindex_done") or 0
        )
        percent = (done / total * 100.0) if total else 0.0
        return {
            "embedding_dim": model.get("embedding_dim"),
            "det_size": model.get("det_size"),
            "reindex_in_progress": in_progress,
            "reindex_done": done,
            "reindex_total": total,
            "reindex_percent": round(percent, 1),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class MnemosLastIdentifySensor(SensorEntity):

    _attr_has_entity_name = True
    _attr_name = "Last identify"
    _attr_icon = "mdi:face-recognition"
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        host: str,
        port: int,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_last_identify"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL_NAME,
            name=f"Mnemos ({host}:{port})",
        )

    async def async_added_to_hass(self) -> None:
        state = get_entry_state(self.hass, self._entry.entry_id)
        self._unsub = state.last_identify_listeners.add(self._on_update)

    async def async_will_remove_from_hass(self) -> None:
        if hasattr(self, "_unsub"):
            self._unsub.discard(self._on_update)

    @callback
    def _on_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        state = get_entry_state(self.hass, self._entry.entry_id)
        payload = state.last_identify
        if not payload:
            return "No identify calls yet"
        persons = payload.get(ATTR_PERSONS) or []
        if persons:
            top = persons[0]
            return f"{top[ATTR_NAME]} ({top[ATTR_CONFIDENCE]:.0%})"
        return "No match"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = get_entry_state(self.hass, self._entry.entry_id)
        payload: dict | None = state.last_identify
        if not payload:
            return {
                "last_run": None,
                "persons": [],
                "unknown": False,
                "took_ms": None,
            }
        return {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "persons": payload.get(ATTR_PERSONS, []),
            "unknown": bool(payload.get(ATTR_UNKNOWN, False)),
            "took_ms": payload.get(ATTR_TOOK_MS),
        }


class _MnemosDiagnosticSensor(
    CoordinatorEntity[MnemosCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: MnemosCoordinator,
        host: str,
        port: int,
        entry: ConfigEntry,
        *,
        unique_suffix: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL_NAME,
            name=f"Mnemos ({host}:{port})",
        )

    def _health(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get(DATA_HEALTH) or {}

    @property
    def available(self) -> bool:
        return bool(self._health())

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class MnemosStatusSensor(_MnemosDiagnosticSensor):
    _attr_name = "Status"
    _attr_icon = "mdi:heart-pulse"

    def __init__(
        self,
        coordinator: MnemosCoordinator,
        host: str,
        port: int,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            host,
            port,
            entry,
            unique_suffix="status",
            name="Status",
            icon="mdi:heart-pulse",
        )

    @property
    def native_value(self) -> str | None:
        return self._health().get(HEALTH_KEY_STATUS)


class MnemosVersionSensor(_MnemosDiagnosticSensor):
    _attr_name = "Version"
    _attr_icon = "mdi:tag-outline"

    def __init__(
        self,
        coordinator: MnemosCoordinator,
        host: str,
        port: int,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            host,
            port,
            entry,
            unique_suffix="version",
            name="Version",
            icon="mdi:tag-outline",
        )

    @property
    def native_value(self) -> str | None:
        return self._health().get(HEALTH_KEY_VERSION)


class MnemosModelLoadedSensor(_MnemosDiagnosticSensor):
    _attr_name = "Model loaded"
    _attr_icon = "mdi:check-decagram"

    def __init__(
        self,
        coordinator: MnemosCoordinator,
        host: str,
        port: int,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            host,
            port,
            entry,
            unique_suffix="model_loaded",
            name="Model loaded",
            icon="mdi:check-decagram",
        )

    @property
    def native_value(self) -> bool | None:
        val = self._health().get(HEALTH_KEY_MODEL_LOADED)
        if val is None:
            return None
        return bool(val)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"model": self._health().get(HEALTH_KEY_MODEL)}
