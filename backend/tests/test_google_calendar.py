"""Coverage for the Google Calendar OAuth + event CRUD service. Network
calls go through a small fake httpx.AsyncClient (same idea as the LLM
provider tests) so nothing here hits the real Google APIs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from jose import jwt

import app.services.google_calendar_service as gcal
from app.core.config import get_settings
from app.models.google_calendar_connection import GoogleCalendarConnection
from app.models.user import User
from app.schemas.google_calendar import CalendarEventCreate, CalendarEventUpdate


# --------------------------------------------------------------------- fakes

class _FakeResponse:
    def __init__(self, *, status_code: int = 200, json_body=None):
        self.status_code = status_code
        self._body = json_body or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeAsyncClient:
    queue: list[_FakeResponse] = []
    calls: list[tuple[str, str, dict]] = []  # (method, url, kwargs)

    def __init__(self, *_, **__):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.queue.pop(0)

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.queue.pop(0)

    async def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.queue.pop(0)


@pytest.fixture(autouse=True)
def _fake_httpx(monkeypatch):
    _FakeAsyncClient.queue = []
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(gcal.httpx, "AsyncClient", _FakeAsyncClient)
    yield


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    """Most tests need a client_id/secret on file; individual tests can
    still exercise the "not configured" path by clearing the cache again."""
    settings = get_settings()
    monkeypatch.setattr(settings, "google_oauth_client_id", "test-client-id")
    from pydantic import SecretStr
    monkeypatch.setattr(settings, "google_oauth_client_secret", SecretStr("test-client-secret"))
    yield


# --------------------------------------------------------------------- authorize URL / state

def test_build_authorize_url_contains_expected_params():
    user_id = uuid.uuid4()
    url = gcal.build_authorize_url(user_id)
    assert url.startswith(gcal.AUTH_URL)
    assert "client_id=test-client-id" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "state=" in url


def test_build_authorize_url_raises_when_not_configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "google_oauth_client_id", "")
    with pytest.raises(gcal.GoogleCalendarNotConfigured):
        gcal.build_authorize_url(uuid.uuid4())


def test_verify_state_round_trips():
    user_id = uuid.uuid4()
    url = gcal.build_authorize_url(user_id)
    state = url.split("state=")[1].split("&")[0]
    # The state param is URL-encoded (JWTs contain '.') — decode it back.
    from urllib.parse import unquote
    assert gcal.verify_state(unquote(state)) == user_id


def test_verify_state_rejects_expired_token():
    settings = get_settings()
    bad_state = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key.get_secret_value(),
        algorithm=gcal.STATE_ALGO,
    )
    with pytest.raises(ValueError):
        gcal.verify_state(bad_state)


# --------------------------------------------------------------------- token exchange

@pytest.mark.asyncio
async def test_exchange_code_creates_connection(session, test_user: User):
    _FakeAsyncClient.queue = [
        _FakeResponse(json_body={"access_token": "at-1", "refresh_token": "rt-1", "expires_in": 3600}),
        _FakeResponse(json_body={"email": "junior@example.com"}),
    ]
    conn = await gcal.exchange_code(session, test_user.id, "auth-code-xyz")
    assert conn.google_email == "junior@example.com"
    assert conn.access_token_encrypted is not None
    assert conn.refresh_token_encrypted is not None
    assert conn.selected_calendar_id == "primary"


@pytest.mark.asyncio
async def test_exchange_code_preserves_existing_refresh_token_when_absent(session, test_user: User):
    existing = GoogleCalendarConnection(
        user_id=test_user.id,
        refresh_token_encrypted=gcal.encrypt("old-refresh-token"),
    )
    session.add(existing)
    await session.commit()

    # Second consent round: Google omits refresh_token (only issued once).
    _FakeAsyncClient.queue = [
        _FakeResponse(json_body={"access_token": "at-2", "expires_in": 3600}),
        _FakeResponse(json_body={"email": "junior@example.com"}),
    ]
    conn = await gcal.exchange_code(session, test_user.id, "auth-code-2")
    assert gcal.decrypt(conn.refresh_token_encrypted) == "old-refresh-token"


# --------------------------------------------------------------------- access token refresh

@pytest.mark.asyncio
async def test_access_token_reused_when_not_expired(session, test_user: User):
    conn = GoogleCalendarConnection(
        user_id=test_user.id,
        access_token_encrypted=gcal.encrypt("still-valid"),
        refresh_token_encrypted=gcal.encrypt("rt"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    session.add(conn)
    await session.commit()

    token = await gcal._access_token(session, conn)
    assert token == "still-valid"
    assert _FakeAsyncClient.calls == []  # no refresh call made


@pytest.mark.asyncio
async def test_access_token_refreshes_when_expired(session, test_user: User):
    conn = GoogleCalendarConnection(
        user_id=test_user.id,
        access_token_encrypted=gcal.encrypt("stale"),
        refresh_token_encrypted=gcal.encrypt("rt-valid"),
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    session.add(conn)
    await session.commit()

    _FakeAsyncClient.queue = [_FakeResponse(json_body={"access_token": "fresh-token", "expires_in": 3600})]
    token = await gcal._access_token(session, conn)
    assert token == "fresh-token"
    assert gcal.decrypt(conn.access_token_encrypted) == "fresh-token"


@pytest.mark.asyncio
async def test_access_token_raises_without_refresh_token(session, test_user: User):
    conn = GoogleCalendarConnection(user_id=test_user.id, token_expires_at=None)
    session.add(conn)
    await session.commit()
    with pytest.raises(gcal.GoogleCalendarNotConnected):
        await gcal._access_token(session, conn)


# --------------------------------------------------------------------- event CRUD

@pytest.mark.asyncio
async def test_list_events_maps_google_shape(session, test_user: User):
    conn = GoogleCalendarConnection(
        user_id=test_user.id,
        access_token_encrypted=gcal.encrypt("tok"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    session.add(conn)
    await session.commit()

    _FakeAsyncClient.queue = [
        _FakeResponse(json_body={"items": [{"id": "primary", "summary": "Primary", "primary": True}]}),
        _FakeResponse(json_body={"items": [
            {"id": "ev1", "summary": "Reunião", "start": {"dateTime": "2026-09-01T10:00:00-03:00"},
             "end": {"dateTime": "2026-09-01T11:00:00-03:00"}, "htmlLink": "https://cal/ev1"},
            {"id": "ev2", "summary": "Feriado", "start": {"date": "2026-09-07"}, "end": {"date": "2026-09-08"}},
        ]}),
    ]
    events = await gcal.list_events(
        session, conn, time_min=datetime.now(timezone.utc), time_max=datetime.now(timezone.utc) + timedelta(days=30)
    )
    assert len(events) == 2
    assert events[0]["all_day"] is False
    assert events[0]["calendar_id"] == "primary"
    assert events[1]["all_day"] is True
    assert events[1]["start"] == "2026-09-07"


@pytest.mark.asyncio
async def test_list_events_merges_across_calendars(session, test_user: User):
    conn = GoogleCalendarConnection(
        user_id=test_user.id,
        access_token_encrypted=gcal.encrypt("tok"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    session.add(conn)
    await session.commit()

    _FakeAsyncClient.queue = [
        _FakeResponse(json_body={"items": [
            {"id": "primary", "summary": "Pessoal", "primary": True},
            {"id": "amparar@group.calendar.google.com", "summary": "Amparar"},
        ]}),
        _FakeResponse(json_body={"items": [
            {"id": "ev-personal", "summary": "Reunião Maçonaria", "start": {"dateTime": "2026-08-17T20:00:00-03:00"},
             "end": {"dateTime": "2026-08-17T22:00:00-03:00"}},
        ]}),
        _FakeResponse(json_body={"items": [
            {"id": "ev-business", "summary": "Reunião de Gestão", "start": {"dateTime": "2026-08-13T10:00:00-03:00"},
             "end": {"dateTime": "2026-08-13T11:00:00-03:00"}},
        ]}),
    ]
    events = await gcal.list_events(
        session, conn, time_min=datetime.now(timezone.utc), time_max=datetime.now(timezone.utc) + timedelta(days=30)
    )
    assert {e["id"] for e in events} == {"ev-personal", "ev-business"}
    assert {e["calendar_id"] for e in events} == {"primary", "amparar@group.calendar.google.com"}
    # sorted chronologically regardless of which calendar they came from
    assert [e["id"] for e in events] == ["ev-business", "ev-personal"]


@pytest.mark.asyncio
async def test_create_event_sends_expected_body(session, test_user: User):
    conn = GoogleCalendarConnection(
        user_id=test_user.id,
        access_token_encrypted=gcal.encrypt("tok"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    session.add(conn)
    await session.commit()

    _FakeAsyncClient.queue = [_FakeResponse(json_body={
        "id": "new1", "summary": "Ligar pro banco",
        "start": {"dateTime": "2026-09-01T09:00:00"}, "end": {"dateTime": "2026-09-01T09:30:00"},
    })]
    data = CalendarEventCreate(
        summary="Ligar pro banco",
        start=datetime(2026, 9, 1, 9, 0),
        end=datetime(2026, 9, 1, 9, 30),
    )
    result = await gcal.create_event(session, conn, data)
    assert result["id"] == "new1"
    method, url, kwargs = _FakeAsyncClient.calls[-1]
    assert method == "POST"
    assert "/calendars/primary/events" in url
    assert kwargs["json"]["summary"] == "Ligar pro banco"


@pytest.mark.asyncio
async def test_update_event_only_sends_provided_fields(session, test_user: User):
    conn = GoogleCalendarConnection(
        user_id=test_user.id,
        access_token_encrypted=gcal.encrypt("tok"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    session.add(conn)
    await session.commit()

    _FakeAsyncClient.queue = [_FakeResponse(json_body={
        "id": "ev1", "summary": "Novo título", "start": {"dateTime": "2026-09-01T09:00:00"}, "end": {"dateTime": "2026-09-01T09:30:00"},
    })]
    await gcal.update_event(session, conn, "primary", "ev1", CalendarEventUpdate(summary="Novo título"))
    _, _, kwargs = _FakeAsyncClient.calls[-1]
    assert kwargs["json"] == {"summary": "Novo título"}


@pytest.mark.asyncio
async def test_delete_event_calls_expected_path(session, test_user: User):
    conn = GoogleCalendarConnection(
        user_id=test_user.id,
        access_token_encrypted=gcal.encrypt("tok"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        selected_calendar_id="me@gmail.com",
    )
    session.add(conn)
    await session.commit()

    _FakeAsyncClient.queue = [_FakeResponse(status_code=204)]
    await gcal.delete_event(session, conn, "me@gmail.com", "ev-to-delete")
    method, url, _ = _FakeAsyncClient.calls[-1]
    assert method == "DELETE"
    assert "me%40gmail.com" in url  # calendar id (an email) is path-encoded
    assert "ev-to-delete" in url


# --------------------------------------------------------------------- API layer

@pytest.mark.asyncio
async def test_status_endpoint_not_connected(client: AsyncClient, auth_headers: dict, test_user: User):
    resp = await client.get("/api/integrations/google-calendar/status", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"connected": False, "google_email": None, "selected_calendar_id": None}


@pytest.mark.asyncio
async def test_connect_endpoint_returns_authorize_url(client: AsyncClient, auth_headers: dict, test_user: User, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "google_oauth_client_id", "test-client-id")
    from pydantic import SecretStr
    monkeypatch.setattr(settings, "google_oauth_client_secret", SecretStr("test-client-secret"))
    resp = await client.get("/api/integrations/google-calendar/connect", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["authorize_url"].startswith(gcal.AUTH_URL)


@pytest.mark.asyncio
async def test_events_endpoint_404_when_not_connected(client: AsyncClient, auth_headers: dict, test_user: User):
    resp = await client.get("/api/integrations/google-calendar/events", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_callback_redirects_on_missing_code(client: AsyncClient):
    resp = await client.get("/api/integrations/google-calendar/callback", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "google_calendar_error=1" in resp.headers["location"]
