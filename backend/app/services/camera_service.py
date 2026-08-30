"""Proxy for Amparar's own camera/NVR server — reachable over Tailscale
only, never from the public internet. The API key lives here and is never
sent to the browser; the frontend always talks to our own /api/cameras/*
routes, which forward the request server-side.
"""
from __future__ import annotations

import re
import time
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


# Stopgap for when the NVR's own channel list drifts from reality —
# cameras physically removed but still registered as channels, or renamed
# on-site without the NVR config following. There's no admin API on that
# server to fix this at the source (probed: no /api/config, /openapi.json,
# or per-camera write endpoints — read-only), so it's patched here
# instead when needed.
#
# Emptied 2026-08-24, one entry added back 2026-08-29 (PVBelve04 — user
# confirmed it no longer physically exists; matches the earlier matriz
# pattern of a dead channel still stuck "connecting" forever). This class
# of drift has recurred before and will again.
#
# (location, name) as returned by /api/cameras -> None to exclude a dead
# channel entirely, or a str to relabel it for display only. Recordings/
# snapshot lookups still use the NVR's real `name` (see list_cameras
# below) — only what's shown to a person changes.
_CAMERA_OVERRIDES: dict[tuple[str, str], Optional[str]] = {
    ("belvedere", "PVBelve04"): None,
}


async def list_cameras() -> list[dict[str, Any]]:
    base, key = _base_and_key()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{base}/api/cameras", headers={"X-Api-Key": key})
        resp.raise_for_status()
        cameras: list[dict[str, Any]] = resp.json()

    out: list[dict[str, Any]] = []
    for cam in cameras:
        key_tuple = (cam.get("location"), cam.get("name"))
        if key_tuple in _CAMERA_OVERRIDES:
            override = _CAMERA_OVERRIDES[key_tuple]
            if override is None:
                continue  # decommissioned — drop it entirely
            cam = {**cam, "display_name": override}
        out.append(cam)
    return out


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


# Agent DVR's audio.mp3 streams indefinitely — there's no natural end to
# cut a request off at, so we impose one here. This turns "live audio"
# into "the frontend re-fetches a fresh clip every ~AUDIO_CHUNK_SECONDS",
# which reuses the exact same authenticated-blob pattern already proven
# for snapshots/recordings instead of needing a new streaming-auth
# mechanism (e.g. a signed query-param token) just for this.
AUDIO_CHUNK_SECONDS = 10.0


async def open_audio_stream(location: str, camera_name: str) -> AsyncIterator[bytes]:
    """Streams up to AUDIO_CHUNK_SECONDS of live audio for one camera, then
    closes — see AUDIO_CHUNK_SECONDS. Raises httpx.HTTPStatusError (404)
    if the camera has no microphone object in Agent DVR."""
    base, key = _base_and_key()
    client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, read=None))
    req = client.build_request(
        "GET", f"{base}/api/audio/{location}/{camera_name}", headers={"X-Api-Key": key}
    )
    resp = await client.send(req, stream=True)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError:
        await resp.aclose()
        await client.aclose()
        raise

    async def _iter() -> AsyncIterator[bytes]:
        started = time.monotonic()
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
                if time.monotonic() - started >= AUDIO_CHUNK_SECONDS:
                    break
        finally:
            await resp.aclose()
            await client.aclose()

    return _iter()
