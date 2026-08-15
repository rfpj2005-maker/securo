import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.post(
        "/api/tasks",
        json={"title": "Cotar placa de ACM", "category": "marketing"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Cotar placa de ACM"
    assert data["category"] == "marketing"
    assert data["status"] == "pending"
    assert data["due_date"] is None


@pytest.mark.asyncio
async def test_create_task_with_due_date(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.post(
        "/api/tasks",
        json={"title": "Contrato Alisson", "category": "administrative", "due_date": "2026-09-01"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["due_date"] == "2026-09-01"


@pytest.mark.asyncio
async def test_create_task_custom_category(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.post(
        "/api/tasks",
        json={"title": "Custom category task", "category": "financeiro"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["category"] == "financeiro"


@pytest.mark.asyncio
async def test_create_task_empty_category_rejected(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.post(
        "/api/tasks",
        json={"title": "Empty category", "category": "  "},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_tasks_filters_by_category_and_status(
    client: AsyncClient, auth_headers: dict, test_user: User
):
    await client.post("/api/tasks", json={"title": "A", "category": "marketing"}, headers=auth_headers)
    await client.post("/api/tasks", json={"title": "B", "category": "management"}, headers=auth_headers)

    response = await client.get("/api/tasks", params={"category": "marketing"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "A"

    response = await client.get("/api/tasks", params={"status": "pending"}, headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_update_task_status(client: AsyncClient, auth_headers: dict, test_user: User):
    create_resp = await client.post(
        "/api/tasks", json={"title": "Estudo viabilidade", "category": "management"}, headers=auth_headers
    )
    task_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/tasks/{task_id}", json={"status": "completed"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, auth_headers: dict, test_user: User):
    create_resp = await client.post(
        "/api/tasks", json={"title": "Ar condicionado", "category": "administrative"}, headers=auth_headers
    )
    task_id = create_resp.json()["id"]

    response = await client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get(f"/api/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_task_404(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.get(
        "/api/tasks/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == 404
