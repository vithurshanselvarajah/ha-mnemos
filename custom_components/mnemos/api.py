from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

from .exceptions import (
    MnemosApiError,
    MnemosAuthError,
    MnemosConnectionError,
    MnemosUnsupportedMedia,
)

_LOGGER = logging.getLogger(__name__)

_HEALTH_TIMEOUT = ClientTimeout(total=10)
_UPLOAD_TIMEOUT = ClientTimeout(total=60)


class MnemosClient:

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        api_key: str,
        use_ssl: bool = False,
    ) -> None:
        self._session = session
        self._api_key = api_key
        scheme = "https" if use_ssl else "http"
        self._base_url = f"{scheme}://{host}:{port}"
        self.base_url = self._base_url

    @property
    def api_key(self) -> str:
        return self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        self._api_key = value

    def _auth_headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        timeout: ClientTimeout,
        **kwargs: Any,
    ) -> dict[str, Any]:
        url = urljoin(self._base_url + "/", path.lstrip("/"))
        headers = self._auth_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        try:
            async with self._session.request(
                method, url, headers=headers, timeout=timeout, **kwargs
            ) as resp:
                try:
                    payload: Any = await resp.json(content_type=None)
                except aiohttp.ContentTypeError:
                    payload = {"detail": await resp.text()}
                if resp.status == 401 or resp.status == 403:
                    raise MnemosAuthError(
                        payload.get("detail") if isinstance(payload, dict) else str(payload)
                    )
                if resp.status >= 400:
                    detail = (
                        payload.get("detail")
                        if isinstance(payload, dict)
                        else str(payload)
                    )
                    raise MnemosApiError(resp.status, detail)
                if not isinstance(payload, dict):
                    raise MnemosApiError(resp.status, "expected JSON object")
                return payload
        except asyncio.TimeoutError as err:
            raise MnemosConnectionError(
                f"Timeout talking to Mnemos at {self._base_url}"
            ) from err
        except ClientResponseError as err:
            raise MnemosApiError(err.status, err.message) from err
        except ClientError as err:
            raise MnemosConnectionError(str(err)) from err

    async def healthz(self) -> dict[str, Any]:
        return await self._request_json("GET", "/healthz", timeout=_HEALTH_TIMEOUT)

    async def model_info(self) -> dict[str, Any]:
        return await self._request_json(
            "GET", "/api/v1/models", timeout=_HEALTH_TIMEOUT
        )

    async def identify(
        self,
        image_bytes: bytes,
        *,
        filename: str = "snapshot.jpg",
        content_type: str = "image/jpeg",
    ) -> dict[str, Any]:
        form = aiohttp.FormData()
        form.add_field(
            "file",
            image_bytes,
            filename=filename,
            content_type=content_type,
        )
        try:
            return await self._request_json(
                "POST",
                "/api/v1/identify",
                data=form,
                timeout=_UPLOAD_TIMEOUT,
            )
        except MnemosApiError as err:
            if err.status == 400 and "Unsupported image" in (err.detail or ""):
                raise MnemosUnsupportedMedia(err.detail) from err
            raise
