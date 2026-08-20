"""Proxy for Amparar's own camera/NVR server — reachable over Tailscale
only, never from the public internet. The API key lives here and is never
sent to the browser; the frontend always talks to our own /api/cameras/*
routes, which forward the request server-side.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Optional

import httpx

from app.core.config import get_settings


class CameraApiNotConfigured(RuntimeError):
    pass


def _base_and_key() -> tuple[str, str]:
    settings = get_settings()
    base = settings.camera_api_base_url.rstrip("/")
    key = settings.camera_api_key.get_secret_value()
    if not base or not key:
        raise CameraApiNotConfigured("CAMERA_API_BASE_URL / CAMERA_API_KEY are not configured.")
    return base, key


async def list_cameras() -> list[dict[str, Any]]:
    base, key = _base_and_key()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{base}/api/cameras", headers={"X-Api-Key": key})
        resp.raise_for_status()
        return resp.json()


async def get_snapshot(location: str, camera_id: str) -> tuple[bytes, str]:
    base, key = _base_and_key()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{base}/api/snapshot/{location}/{camera_id}", headers={"X-Api-Key": key}
        )
        resp.raise_for_status()
        return resp.content, resp.headers.get("content-type", "image/jpeg")


async def list_recordings(location: str, camera_name: str) -> list[dict[str, Any]]:
    base, key = _base_and_key()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{base}/api/recordings/{location}/{camera_name}", headers={"X-Api-Key": key}
        )
        resp.raise_for_status()
        return resp.json()


async def open_recording_stream(
    location: str, camera_name: str, filename: str
) -> tuple[str, Optional[int], AsyncIterator[bytes]]:
    """Opens the upstream recording and returns (content_type,
    content_length, byte iterator). Streams through rather than buffering
    fully in memory — clips can run for several minutes. The client that
    owns the connection is closed automatically once the iterator is
    exhausted or the consumer stops early."""
    base, key = _base_and_key()
    client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, read=120.0))
    req = client.build_request(
        "GET", f"{base}/api/recording/{location}/{camera_name}/{filename}", headers={"X-Api-Key": key}
    )
    resp = await client.send(req, stream=True)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError:
        await resp.aclose()
        await client.aclose()
        raise
    content_length = resp.headers.get("content-length")
    content_type = resp.headers.get("content-type", "video/mp4")

    async def _iter() -> AsyncIterator[bytes]:
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return content_type, int(content_length) if content_length else None, _iter()
