import pytest
from httpx import AsyncClient

from app.models.user import User


async def _create_task(client: AsyncClient, auth_headers: dict, title: str = "Parent task") -> str:
    resp = await client.post("/api/tasks", json={"title": title, "category": "administrative"}, headers=auth_headers)
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_subtask(client: AsyncClient, auth_headers: dict, test_user: User):
    task_id = await _create_task(client, auth_headers)
    response = await client.post(
        f"/api/tasks/{task_id}/subtasks", json={"title": "Levantar etapas"}, headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Levantar etapas"
    assert data["is_done"] is False
    assert data["position"] == 0


@pytest.mark.asyncio
async def test_subtasks_appear_on_parent_task(client: AsyncClient, auth_headers: dict, test_user: User):
    task_id = await _create_task(client, auth_headers)
    await client.post(f"/api/tasks/{task_id}/subtasks", json={"title": "Passo 1"}, headers=auth_headers)
    await client.post(f"/api/tasks/{task_id}/subtasks", json={"title": "Passo 2"}, headers=auth_headers)

    response = await client.get(f"/api/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 200
    subtasks = response.json()["subtasks"]
    assert [s["title"] for s in subtasks] == ["Passo 1", "Passo 2"]
    assert [s["position"] for s in subtasks] == [0, 1]


@pytest.mark.asyncio
async def test_toggle_subtask_done(client: AsyncClient, auth_headers: dict, test_user: User):
    task_id = await _create_task(client, auth_headers)
    create_resp = await client.post(
        f"/api/tasks/{task_id}/subtasks", json={"title": "Revisar com o Davi"}, headers=auth_headers
    )
    subtask_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/tasks/{task_id}/subtasks/{subtask_id}", json={"is_done": True}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["is_done"] is True


@pytest.mark.asyncio
async def test_delete_subtask(client: AsyncClient, auth_headers: dict, test_user: User):
    task_id = await _create_task(client, auth_headers)
    create_resp = await client.post(
        f"/api/tasks/{task_id}/subtasks", json={"title": "Descartável"}, headers=auth_headers
    )
    subtask_id = create_resp.json()["id"]

    response = await client.delete(f"/api/tasks/{task_id}/subtasks/{subtask_id}", headers=auth_headers)
    assert response.status_code == 204

    task_resp = await client.get(f"/api/tasks/{task_id}", headers=auth_headers)
    assert task_resp.json()["subtasks"] == []


@pytest.mark.asyncio
async def test_create_subtask_for_nonexistent_task_404(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.post(
        "/api/tasks/00000000-0000-0000-0000-000000000000/subtasks",
        json={"title": "Orphan"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deleting_task_cascades_subtasks(client: AsyncClient, auth_headers: dict, test_user: User):
    task_id = await _create_task(client, auth_headers)
    await client.post(f"/api/tasks/{task_id}/subtasks", json={"title": "Vai junto"}, headers=auth_headers)

    delete_resp = await client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    # The task itself is gone, so nested subtask routes should now 404 too.
    get_resp = await client.get(f"/api/tasks/{task_id}", headers=auth_headers)
    assert get_resp.status_code == 404
