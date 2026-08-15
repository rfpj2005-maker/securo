"""Google Calendar integration: OAuth2 (authorization-code + refresh) and a
thin wrapper over the Calendar API v3 REST endpoints. No google-api-python-
client dependency — plain httpx, matching the rest of the codebase's style
for third-party HTTP integrations (Pluggy, Siprov, etc.).
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote, urlencode

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.services.crypto import decrypt, encrypt
from app.core.config import get_settings
from app.models.google_calendar_connection import GoogleCalendarConnection
from app.schemas.google_calendar import CalendarEventCreate, CalendarEventUpdate

logger = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
CALENDAR_API = "https://www.googleapis.com/calendar/v3"
SCOPES = "https://www.googleapis.com/auth/calendar openid email"

STATE_ALGO = "HS256"


class GoogleCalendarNotConfigured(RuntimeError):
    pass


class GoogleCalendarNotConnected(RuntimeError):
    pass


def _client_credentials() -> tuple[str, str]:
    settings = get_settings()
    client_id = settings.google_oauth_client_id
    client_secret = settings.google_oauth_client_secret.get_secret_value()
    if not client_id or not client_secret:
        raise GoogleCalendarNotConfigured("Google OAuth client ID/secret are not configured")
    return client_id, client_secret


def _redirect_uri() -> str:
    return f"{get_settings().frontend_url.rstrip('/')}/api/integrations/google-calendar/callback"


def build_authorize_url(user_id: uuid.UUID) -> str:
    client_id, _ = _client_credentials()
    state = jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        get_settings().secret_key.get_secret_value(),
        algorithm=STATE_ALGO,
    )
    params = {
        "client_id": client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def verify_state(state: str) -> uuid.UUID:
    try:
        payload = jwt.decode(state, get_settings().secret_key.get_secret_value(), algorithms=[STATE_ALGO])
    except JWTError as exc:
        raise ValueError("invalid or expired state") from exc
    return uuid.UUID(payload["sub"])


async def exchange_code(session: AsyncSession, user_id: uuid.UUID, code: str) -> GoogleCalendarConnection:
    client_id, client_secret = _client_credentials()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()

        userinfo_resp = await client.get(
            USERINFO_URL, headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        userinfo_resp.raise_for_status()
        email = userinfo_resp.json().get("email")

    conn = await get_connection(session, user_id)
    if conn is None:
        conn = GoogleCalendarConnection(user_id=user_id)
        session.add(conn)

    conn.google_email = email
    conn.access_token_encrypted = encrypt(tokens["access_token"])
    if tokens.get("refresh_token"):
        # Google only returns a refresh_token on first consent (or when
        # prompt=consent forces re-issue, which we always pass) — never
        # overwrite a previously stored one with an absent value.
        conn.refresh_token_encrypted = encrypt(tokens["refresh_token"])
    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))

    await session.commit()
    await session.refresh(conn)
    return conn


async def get_connection(session: AsyncSession, user_id: uuid.UUID) -> Optional[GoogleCalendarConnection]:
    return (
        await session.execute(select(GoogleCalendarConnection).where(GoogleCalendarConnection.user_id == user_id))
    ).scalar_one_or_none()


async def disconnect(session: AsyncSession, user_id: uuid.UUID) -> bool:
    conn = await get_connection(session, user_id)
    if conn is None:
        return False
    await session.delete(conn)
    await session.commit()
    return True


async def set_selected_calendar(session: AsyncSession, user_id: uuid.UUID, calendar_id: str) -> Optional[GoogleCalendarConnection]:
    conn = await get_connection(session, user_id)
    if conn is None:
        return None
    conn.selected_calendar_id = calendar_id
    await session.commit()
    await session.refresh(conn)
    return conn


async def _access_token(session: AsyncSession, conn: GoogleCalendarConnection) -> str:
    """Return a valid access token, refreshing it first if it's expired
    (or about to expire in the next minute)."""
    now = datetime.now(timezone.utc)
    if conn.token_expires_at and conn.token_expires_at > now + timedelta(minutes=1) and conn.access_token_encrypted:
        token = decrypt(conn.access_token_encrypted)
        if token:
            return token

    refresh_token = decrypt(conn.refresh_token_encrypted)
    if not refresh_token:
        raise GoogleCalendarNotConnected("No refresh token on file — reconnect Google Calendar")

    client_id, client_secret = _client_credentials()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()

    conn.access_token_encrypted = encrypt(tokens["access_token"])
    conn.token_expires_at = now + timedelta(seconds=tokens.get("expires_in", 3600))
    await session.commit()
    return tokens["access_token"]


async def _calendar_request(
    session: AsyncSession, conn: GoogleCalendarConnection, method: str, path: str, **kwargs: Any
) -> httpx.Response:
    token = await _access_token(session, conn)
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.request(
            method, f"{CALENDAR_API}{path}", headers={"Authorization": f"Bearer {token}"}, **kwargs
        )
        resp.raise_for_status()
        return resp


async def list_calendars(session: AsyncSession, conn: GoogleCalendarConnection) -> list[dict[str, Any]]:
    resp = await _calendar_request(session, conn, "GET", "/users/me/calendarList")
    items = resp.json().get("items", [])
    return [
        {"id": c["id"], "summary": c.get("summary", c["id"]), "primary": bool(c.get("primary"))} for c in items
    ]


def _event_to_read(ev: dict[str, Any], calendar_id: str, calendar_summary: Optional[str] = None) -> dict[str, Any]:
    start = ev.get("start", {})
    end = ev.get("end", {})
    all_day = "date" in start
    return {
        "id": ev["id"],
        "summary": ev.get("summary", "(sem título)"),
        "description": ev.get("description"),
        "location": ev.get("location"),
        "start": start.get("date") or start.get("dateTime"),
        "end": end.get("date") or end.get("dateTime"),
        "all_day": all_day,
        "html_link": ev.get("htmlLink"),
        "calendar_id": calendar_id,
        "calendar_summary": calendar_summary,
    }


def _cal_path(calendar_id: str) -> str:
    """Calendar IDs are often the account's email address, which needs
    path-safe percent-encoding (the @ especially)."""
    return quote(calendar_id, safe="")


async def list_events(
    session: AsyncSession, conn: GoogleCalendarConnection, *, time_min: datetime, time_max: datetime
) -> list[dict[str, Any]]:
    """Merges events from every calendar on the account (not just the
    "selected" one) — a personal account commonly splits events across
    several calendars (e.g. a business calendar + a personal one), and
    users expect one combined view."""
    calendars = await list_calendars(session, conn)

    async def _fetch(cal: dict[str, Any]) -> list[dict[str, Any]]:
        resp = await _calendar_request(
            session,
            conn,
            "GET",
            f"/calendars/{_cal_path(cal['id'])}/events",
            params={
                "timeMin": time_min.isoformat(),
                "timeMax": time_max.isoformat(),
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": 250,
            },
        )
        return [_event_to_read(ev, cal["id"], cal["summary"]) for ev in resp.json().get("items", [])]

    results = await asyncio.gather(*[_fetch(cal) for cal in calendars], return_exceptions=True)
    events: list[dict[str, Any]] = []
    for cal, result in zip(calendars, results):
        if isinstance(result, BaseException):
            logger.warning("failed to fetch events for calendar %s: %s", cal["id"], result)
            continue
        events.extend(result)
    events.sort(key=lambda e: e["start"])
    return events


def _to_google_time(dt: datetime, all_day: bool) -> dict[str, str]:
    if all_day:
        return {"date": dt.date().isoformat()}
    return {"dateTime": dt.isoformat()}


async def create_event(
    session: AsyncSession, conn: GoogleCalendarConnection, data: CalendarEventCreate
) -> dict[str, Any]:
    body = {
        "summary": data.summary,
        "description": data.description,
        "location": data.location,
        "start": _to_google_time(data.start, data.all_day),
        "end": _to_google_time(data.end, data.all_day),
    }
    resp = await _calendar_request(
        session, conn, "POST", f"/calendars/{_cal_path(conn.selected_calendar_id)}/events", json=body
    )
    return _event_to_read(resp.json(), conn.selected_calendar_id)


async def update_event(
    session: AsyncSession,
    conn: GoogleCalendarConnection,
    calendar_id: str,
    event_id: str,
    data: CalendarEventUpdate,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if data.summary is not None:
        body["summary"] = data.summary
    if data.description is not None:
        body["description"] = data.description
    if data.location is not None:
        body["location"] = data.location
    if data.start is not None:
        body["start"] = _to_google_time(data.start, bool(data.all_day))
    if data.end is not None:
        body["end"] = _to_google_time(data.end, bool(data.all_day))
    resp = await _calendar_request(
        session, conn, "PATCH", f"/calendars/{_cal_path(calendar_id)}/events/{quote(event_id, safe='')}", json=body
    )
    return _event_to_read(resp.json(), calendar_id)


async def delete_event(session: AsyncSession, conn: GoogleCalendarConnection, calendar_id: str, event_id: str) -> None:
    await _calendar_request(
        session, conn, "DELETE", f"/calendars/{_cal_path(calendar_id)}/events/{quote(event_id, safe='')}"
    )
