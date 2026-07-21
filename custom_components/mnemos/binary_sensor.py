from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_HEALTH,
    DOMAIN,
    HEALTH_KEY_STATUS,
    HEALTH_KEY_VECTOR_DB,
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
    async_add_entities([MnemosReachableBinarySensor(state.coordinator, host, port, entry)])


class MnemosReachableBinarySensor(
    CoordinatorEntity[MnemosCoordinator], BinarySensorEntity
):

    _attr_has_entity_name = True
    _attr_name = "Reachable"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
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
        self._attr_unique_id = f"{entry.entry_id}_reachable"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL_NAME,
            name=f"Mnemos ({host}:{port})",
        )

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        health = self.coordinator.data.get(DATA_HEALTH) or {}
        if not health:
            return None
        return (
            health.get(HEALTH_KEY_STATUS) == "ok"
            and health.get(HEALTH_KEY_VECTOR_DB) is True
        )

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {
                "version": None,
                "model": None,
                "db": None,
                "vector_db": None,
                "reindex_in_progress": None,
                "reindex_done": None,
                "reindex_total": None,
                "last_success": None,
                "last_error": self.coordinator.last_error,
            }
        health = self.coordinator.data.get(DATA_HEALTH) or {}
        last_success = self.coordinator.last_success
        return {
            "version": health.get("version"),
            "model": health.get("model"),
            "db": health.get("db"),
            "vector_db": health.get("vector_db"),
            "reindex_in_progress": health.get("reindex_in_progress"),
            "reindex_done": health.get("reindex_done"),
            "reindex_total": health.get("reindex_total"),
            "last_success": (
                last_success.replace(tzinfo=timezone.utc).isoformat()
                if last_success is not None
                else None
            ),
            "last_error": self.coordinator.last_error,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
