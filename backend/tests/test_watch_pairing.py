from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


def _make_redis_mock_with_store():
    """Redis mock that actually stores key-value pairs, including NX
    semantics — the pairing code generator relies on SET NX to avoid a
    freak collision with another still-live code."""
    store: dict[str, str] = {}
    mock = AsyncMock()

    async def mock_get(key):
        return store.get(key)

    async def mock_set(key, value, ex=None, nx=False):
        if nx and key in store:
            return None
        store[key] = value
        return True

    async def mock_delete(key):
        store.pop(key, None)

    mock.get = AsyncMock(side_effect=mock_get)
    mock.set = AsyncMock(side_effect=mock_set)
    mock.delete = AsyncMock(side_effect=mock_delete)

    pipe_mock = MagicMock()
    pipe_mock.execute = AsyncMock(return_value=[0, 0, True, True])
    mock.pipeline = lambda: pipe_mock

    return mock


@pytest.fixture(autouse=True)
def _override_redis_with_store(_mock_redis):
    """Override the autouse _mock_redis with one that has a real store."""
    mock = _make_redis_mock_with_store()

    async def _fake():
        return mock

    with patch("app.core.redis.get_redis", _fake), \
         patch("app.core.rate_limit.get_redis", _fake), \
         patch("app.api.watch_pairing.get_redis", _fake):
        yield mock


async def test_start_watch_pairing_returns_code(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/auth/watch-pair/start", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["code"]) == 6
    assert data["code"].isdigit()
    assert data["expires_in"] == 600


async def test_start_watch_pairing_requires_auth(client: AsyncClient):
    resp = await client.post("/api/auth/watch-pair/start")
    assert resp.status_code == 401


async def test_redeem_watch_pairing_success(client: AsyncClient, auth_headers: dict):
    start_resp = await client.post("/api/auth/watch-pair/start", headers=auth_headers)
    code = start_resp.json()["code"]

    resp = await client.post("/api/auth/watch-pair/redeem", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"

    # The redeemed token actually authenticates as the pairing user.
    whoami = await client.get(
        "/api/tasks", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert whoami.status_code == 200


async def test_redeem_watch_pairing_invalid_code(client: AsyncClient):
    resp = await client.post("/api/auth/watch-pair/redeem", json={"code": "000000"})
    assert resp.status_code == 401


async def test_redeem_watch_pairing_is_one_time_use(client: AsyncClient, auth_headers: dict):
    start_resp = await client.post("/api/auth/watch-pair/start", headers=auth_headers)
    code = start_resp.json()["code"]

    first = await client.post("/api/auth/watch-pair/redeem", json={"code": code})
    assert first.status_code == 200

    second = await client.post("/api/auth/watch-pair/redeem", json={"code": code})
    assert second.status_code == 401


async def test_redeem_watch_pairing_rejects_malformed_code(client: AsyncClient):
    resp = await client.post("/api/auth/watch-pair/redeem", json={"code": "abc"})
    assert resp.status_code == 422
