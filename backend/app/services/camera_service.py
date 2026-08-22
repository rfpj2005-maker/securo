"""Proxy for Amparar's own camera/NVR server — reachable over Tailscale
only, never from the public internet. The API key lives here and is never
sent to the browser; the frontend always talks to our own /api/cameras/*
routes, which forward the request server-side.
"""
from __future__ import annotations

import re
from datetime import date as date_cls, datetime, time as time_cls, timezone
from typing import Any, AsyncIterator, Optional
from zoneinfo import ZoneInfo

import httpx

from app.core.config import get_settings

# The recording server stamps the true event start into the filename
# itself, already in local time (e.g. "1_2026-08-20_16-36-05_411.mp4") —
# several seconds before `modified`, which is when the file finished
# writing to disk. Search/sort by the filename timestamp; fall back to
# `modified` (converted from UTC) only if a filename doesn't match.
_FILENAME_TIMESTAMP = re.compile(r"_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})_")
_LOCAL_TZ = ZoneInfo("America/Sao_Paulo")


def recording_datetime(rec: dict[str, Any]) -> datetime:
    match = _FILENAME_TIMESTAMP.search(rec.get("filename") or "")
    if match:
        d, hh, mm, ss = match.groups()
        return datetime.fromisoformat(f"{d}T{hh}:{mm}:{ss}")
    modified = rec.get("modified")
    if modified:
        dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_LOCAL_TZ).replace(tzinfo=None)
    return datetime.min


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


async def search_recordings(
    location: str,
    camera_name: str,
    *,
    on_date: Optional[date_cls] = None,
    time_from: Optional[time_cls] = None,
    time_to: Optional[time_cls] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Filters one camera's recordings by calendar day and/or time-of-day
    range. The upstream API has no filtering of its own — it always
    returns the full list (hundreds of clips isn't unusual) — so this
    fetches everything once and filters here."""
    all_recs = await list_recordings(location, camera_name)
    matches: list[dict[str, Any]] = []
    for rec in all_recs:
        dt = recording_datetime(rec)
        if on_date is not None and dt.date() != on_date:
            continue
        if time_from is not None and dt.time() < time_from:
            continue
        if time_to is not None and dt.time() > time_to:
            continue
        matches.append({**rec, "recorded_at": dt.isoformat()})
    matches.sort(key=lambda r: r["recorded_at"], reverse=True)
    return matches[:limit]


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
