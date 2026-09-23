from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.models.user import User


async def _create_vehicle(client: AsyncClient, headers: dict, **overrides) -> dict:
    payload = {"name": "Onix", "plate": "abc1d23", "fuel_type": "flex", "initial_odometer": 10000}
    payload.update(overrides)
    response = await client.post("/api/vehicles", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def _add_record(client: AsyncClient, headers: dict, vehicle_id: str, **payload) -> dict:
    response = await client.post(f"/api/vehicles/{vehicle_id}/records", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_create_vehicle(client: AsyncClient, auth_headers: dict, test_user: User):
    data = await _create_vehicle(client, auth_headers, brand="Chevrolet", model="Onix LT", year=2022)
    assert data["name"] == "Onix"
    assert data["plate"] == "ABC1D23"
    assert data["year"] == 2022
    assert data["is_active"] is True
    stats = data["stats"]
    assert stats["current_odometer"] == 10000
    assert stats["distance"] == 0
    assert stats["total_cost"] == "0.00"
    assert stats["avg_consumption"] is None
    assert stats["cost_per_km"] is None


@pytest.mark.asyncio
async def test_create_vehicle_rejects_unknown_fuel(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.post(
        "/api/vehicles", json={"name": "X", "fuel_type": "plutonium"}, headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_and_list_vehicles(client: AsyncClient, auth_headers: dict, test_user: User):
    onix = await _create_vehicle(client, auth_headers)
    await _create_vehicle(client, auth_headers, name="Hilux", plate="XYZ9A87", fuel_type="diesel")

    response = await client.patch(
        f"/api/vehicles/{onix['id']}", json={"is_active": False}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    response = await client.get("/api/vehicles", headers=auth_headers)
    assert [v["name"] for v in response.json()] == ["Hilux", "Onix"]

    response = await client.get("/api/vehicles", params={"include_inactive": False}, headers=auth_headers)
    assert [v["name"] for v in response.json()] == ["Hilux"]


@pytest.mark.asyncio
async def test_delete_vehicle_cascades(client: AsyncClient, auth_headers: dict, test_user: User):
    vehicle = await _create_vehicle(client, auth_headers)
    await _add_record(client, auth_headers, vehicle["id"], kind="fuel", date="2026-09-01", amount="200", liters="35")

    response = await client.delete(f"/api/vehicles/{vehicle['id']}", headers=auth_headers)
    assert response.status_code == 204
    response = await client.get(f"/api/vehicles/{vehicle['id']}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_fuel_consumption_and_stats(client: AsyncClient, auth_headers: dict, test_user: User):
    vehicle = await _create_vehicle(client, auth_headers)
    vid = vehicle["id"]

    # Anchor fill-up: tank topped off, no consumption yet.
    first = await _add_record(
        client, auth_headers, vid, kind="fuel", date="2026-09-01", odometer=10000, amount="250", liters="40"
    )
    assert first["consumption"] is None
    # Partial fill-up in between: its liters count toward the next interval.
    await _add_record(
        client, auth_headers, vid, kind="fuel", date="2026-09-05", odometer=10200,
        amount="60", liters="10", full_tank=False,
    )
    # Closes the interval: 500 km / (10 + 30) L = 12.5 km/L.
    closing = await _add_record(
        client, auth_headers, vid, kind="fuel", date="2026-09-10", odometer=10500, amount="180", liters="30"
    )
    assert closing["consumption"] == "12.50"

    await _add_record(
        client, auth_headers, vid, kind="maintenance", date="2026-09-12", odometer=10550,
        amount="400", liters="99", description="Troca de óleo",
    )

    response = await client.get(f"/api/vehicles/{vid}", headers=auth_headers)
    stats = response.json()["stats"]
    assert stats["current_odometer"] == 10550
    assert stats["distance"] == 550
    assert stats["fuel_cost"] == "490.00"
    assert stats["maintenance_cost"] == "400.00"
    assert stats["total_cost"] == "890.00"
    assert stats["avg_consumption"] == "12.50"
    assert stats["cost_per_km"] == "1.62"
    # Liters on a maintenance record are dropped, so they don't count.
    assert float(stats["total_liters"]) == 80.0

    records = (await client.get(f"/api/vehicles/{vid}/records", headers=auth_headers)).json()
    assert [r["kind"] for r in records] == ["maintenance", "fuel", "fuel", "fuel"]
    assert records[0]["liters"] is None


@pytest.mark.asyncio
async def test_update_and_delete_record(client: AsyncClient, auth_headers: dict, test_user: User):
    vehicle = await _create_vehicle(client, auth_headers)
    record = await _add_record(client, auth_headers, vehicle["id"], kind="expense", date="2026-09-01", amount="15")

    response = await client.patch(
        f"/api/vehicles/{vehicle['id']}/records/{record['id']}",
        json={"amount": "20", "description": "Estacionamento"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["amount"] == "20.00"
    assert response.json()["description"] == "Estacionamento"

    response = await client.delete(f"/api/vehicles/{vehicle['id']}/records/{record['id']}", headers=auth_headers)
    assert response.status_code == 204
    response = await client.get(f"/api/vehicles/{vehicle['id']}/records", headers=auth_headers)
    assert response.json() == []


@pytest.mark.asyncio
async def test_record_on_missing_vehicle_is_404(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.post(
        "/api/vehicles/00000000-0000-0000-0000-000000000000/records",
        json={"kind": "fuel", "date": "2026-09-01", "amount": "10"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reminders_overdue_by_date_and_odometer(client: AsyncClient, auth_headers: dict, test_user: User):
    vehicle = await _create_vehicle(client, auth_headers)
    vid = vehicle["id"]
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    next_month = (date.today() + timedelta(days=30)).isoformat()

    ipva = await client.post(
        f"/api/vehicles/{vid}/reminders", json={"title": "IPVA", "due_date": yesterday}, headers=auth_headers
    )
    assert ipva.status_code == 201
    assert ipva.json()["is_overdue"] is True

    oil = await client.post(
        f"/api/vehicles/{vid}/reminders", json={"title": "Troca de óleo", "due_odometer": 15000}, headers=auth_headers
    )
    assert oil.json()["is_overdue"] is False

    await client.post(
        f"/api/vehicles/{vid}/reminders", json={"title": "Seguro", "due_date": next_month}, headers=auth_headers
    )

    # Driving past the due odometer makes the oil change overdue.
    await _add_record(client, auth_headers, vid, kind="fuel", date="2026-09-01", odometer=15100, amount="100", liters="20")
    reminders = (await client.get(f"/api/vehicles/{vid}/reminders", headers=auth_headers)).json()
    by_title = {r["title"]: r for r in reminders}
    assert by_title["Troca de óleo"]["is_overdue"] is True
    assert by_title["Seguro"]["is_overdue"] is False

    stats = (await client.get(f"/api/vehicles/{vid}", headers=auth_headers)).json()["stats"]
    assert stats["pending_reminders"] == 3
    assert stats["overdue_reminders"] == 2

    response = await client.patch(
        f"/api/vehicles/{vid}/reminders/{ipva.json()['id']}", json={"is_done": True}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["is_overdue"] is False

    response = await client.delete(f"/api/vehicles/{vid}/reminders/{oil.json()['id']}", headers=auth_headers)
    assert response.status_code == 204
    stats = (await client.get(f"/api/vehicles/{vid}", headers=auth_headers)).json()["stats"]
    assert stats["pending_reminders"] == 1
    assert stats["overdue_reminders"] == 0
