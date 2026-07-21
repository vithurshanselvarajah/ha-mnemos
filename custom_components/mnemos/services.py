from __future__ import annotations

import logging
import os
import time
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import slugify

from .const import (
    ATTR_CONFIDENCE,
    ATTR_NAME,
    ATTR_PERSONS,
    ATTR_TOOK_MS,
    ATTR_UNKNOWN,
    DEFAULT_TIMEOUT,
    DOMAIN,
    SERVICE_FIELD_ENTITY_ID,
    SERVICE_FIELD_FILE_PATH,
    SERVICE_FIELD_TIMEOUT,
    SERVICE_IDENTIFY,
    SERVICE_REFRESH,
)
from .exceptions import (
    MnemosAuthError,
    MnemosConnectionError,
    MnemosUnsupportedMedia,
)
from .state import list_entry_states, resolve_entry_state

_LOGGER = logging.getLogger(__name__)


def _coerce_match(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        ATTR_NAME: raw.get("name", ""),
        ATTR_CONFIDENCE: float(raw.get("confidence", 0.0)),
    }


IDENTIFY_SCHEMA = vol.Schema(
    {
        vol.Exclusive(SERVICE_FIELD_ENTITY_ID, "source"): cv.entity_id,
        vol.Exclusive(SERVICE_FIELD_FILE_PATH, "source"): cv.string,
        vol.Optional(SERVICE_FIELD_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=120)
        ),
    }
)


async def _read_camera(call: ServiceCall) -> tuple[bytes, str, str, str]:
    from homeassistant.components.camera import async_get_image

    entity_id: str = call.data[SERVICE_FIELD_ENTITY_ID]
    timeout = call.data.get(SERVICE_FIELD_TIMEOUT, DEFAULT_TIMEOUT)
    try:
        image = await async_get_image(call.hass, entity_id, timeout=timeout)
    except Exception as err:  # noqa: BLE001
        raise HomeAssistantError(
            f"Failed to fetch image from {entity_id}: {err}"
        ) from err
    filename = f"{slugify(entity_id)}.jpg"
    content_type = image.content_type or "image/jpeg"
    return image.content, filename, content_type, entity_id


async def _read_file(call: ServiceCall) -> tuple[bytes, str, str, str]:
    path: str = call.data[SERVICE_FIELD_FILE_PATH]
    if not await call.hass.async_add_executor_job(os.path.isfile, path):
        raise ServiceValidationError(f"file_path does not exist: {path}")

    def _read() -> bytes:
        with open(path, "rb") as f:
            return f.read()

    data = await call.hass.async_add_executor_job(_read)
    if not data:
        raise ServiceValidationError(f"file_path is empty: {path}")
    name = os.path.basename(path) or "snapshot.jpg"
    lower = name.lower()
    if lower.endswith(".png"):
        content_type = "image/png"
    elif lower.endswith(".webp"):
        content_type = "image/webp"
    else:
        content_type = "image/jpeg"
    return data, name, content_type, path


async def _dispatch_identify(call: ServiceCall) -> ServiceResponse:
    has_entity = SERVICE_FIELD_ENTITY_ID in call.data
    has_path = SERVICE_FIELD_FILE_PATH in call.data
    if not has_entity and not has_path:
        raise ServiceValidationError(
            "Provide either `entity_id` (camera) or `file_path`."
        )

    state = resolve_entry_state(call.hass)

    if has_entity:
        image_bytes, filename, content_type, source = await _read_camera(call)
    else:
        image_bytes, filename, content_type, source = await _read_file(call)

    started = time.monotonic()
    try:
        result = await state.client.identify(
            image_bytes, filename=filename, content_type=content_type
        )
    except MnemosUnsupportedMedia as err:
        raise HomeAssistantError(f"Mnemos could not decode the image: {err}") from err
    except MnemosAuthError as err:
        raise HomeAssistantError(
            "Mnemos rejected the API key. Re-add the integration with a valid Identify-Only key."
        ) from err
    except MnemosConnectionError as err:
        raise HomeAssistantError(f"Could not reach Mnemos: {err}") from err
    took_ms = int((time.monotonic() - started) * 1000)

    matched = [_coerce_match(m) for m in (result.get("recognized") or [])]
    has_unknown = bool(result.get("unknown_faces"))

    response: ServiceResponse = {
        ATTR_PERSONS: matched,
        ATTR_UNKNOWN: has_unknown,
        ATTR_TOOK_MS: took_ms,
    }
    state.set_last_identify(response)

    if matched:
        top = matched[0]
        _LOGGER.info(
            "mnemos.identify: matched %s (%.0f%%) — %d matched, unknown=%s in %d ms",
            top[ATTR_NAME],
            top[ATTR_CONFIDENCE] * 100,
            len(matched),
            has_unknown,
            took_ms,
        )
    else:
        _LOGGER.info(
            "mnemos.identify: no matches, unknown=%s in %d ms",
            has_unknown,
            took_ms,
        )
    return response


async def _dispatch_refresh(call: ServiceCall) -> None:
    for state in list_entry_states(call.hass):
        await state.coordinator.async_request_refresh()


def async_register_services(hass: HomeAssistant) -> None:
    async def identify(call: ServiceCall) -> None:
        await _dispatch_identify(call)

    async def refresh(call: ServiceCall) -> None:
        await _dispatch_refresh(call)

    hass.services.async_register(
        DOMAIN, SERVICE_IDENTIFY, identify, schema=IDENTIFY_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_REFRESH, refresh)


def async_unregister_services(hass: HomeAssistant) -> None:
    hass.services.async_remove(DOMAIN, SERVICE_IDENTIFY)
    hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
