from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.task import TaskCreate, TaskUpdate
from app.services import subtask_service, task_service
from mcp_server.auth import CallContext
from mcp_server.registry import tool
from mcp_server.tools._helpers import parse_date, parse_uuid, resolve_workspace_id


def _task_to_dict(t: Any) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "title": t.title,
        "category": t.category,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "status": t.status,
        "subtasks": [
            {"id": str(s.id), "title": s.title, "is_done": s.is_done} for s in t.subtasks
        ],
    }


@tool(
    name="list_tasks",
    description="List the user's to-do tasks, optionally filtered by category or status (pending/completed).",
    parameters={
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Filter by category (free text, e.g. 'marketing')"},
            "status": {"type": "string", "enum": ["pending", "completed"]},
        },
        "additionalProperties": False,
    },
    tags=["read", "tasks"],
)
async def list_tasks(
    *, session: AsyncSession, ctx: CallContext, category: str | None = None, status: str | None = None
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    rows = await task_service.get_tasks(session, ws_id, category=category, status=status)
    return {"items": [_task_to_dict(t) for t in rows], "total": len(rows)}


@tool(
    name="create_task",
    description="Create a new to-do task for the user.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "category": {"type": "string", "description": "Free text, e.g. 'marketing', 'administrative'. Defaults to 'administrative'."},
            "due_date": {"type": "string", "format": "date", "description": "YYYY-MM-DD, optional"},
        },
        "required": ["title"],
        "additionalProperties": False,
    },
    tags=["write", "tasks"],
)
async def create_task(
    *, session: AsyncSession, ctx: CallContext, title: str, category: str = "administrative", due_date: str | None = None
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    data = TaskCreate(title=title, category=category, due_date=parse_date(due_date))
    t = await task_service.create_task(session, ws_id, ctx.user_id, data)
    return _task_to_dict(t)


@tool(
    name="update_task",
    description="Update a task's title, category, due date, and/or status (pending/completed).",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "title": {"type": "string"},
            "category": {"type": "string"},
            "due_date": {"type": "string", "format": "date"},
            "status": {"type": "string", "enum": ["pending", "completed"]},
        },
        "required": ["task_id"],
        "additionalProperties": False,
    },
    tags=["write", "tasks"],
)
async def update_task(
    *,
    session: AsyncSession,
    ctx: CallContext,
    task_id: str,
    title: str | None = None,
    category: str | None = None,
    due_date: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    data = TaskUpdate(
        title=title,
        category=category,
        due_date=parse_date(due_date) if due_date is not None else None,
        status=status,
    )
    t = await task_service.update_task(session, parse_uuid(task_id), ws_id, data)
    if t is None:
        raise ValueError(f"Task {task_id} not found")
    return _task_to_dict(t)


@tool(
    name="delete_task",
    description="Delete a task (and its subtasks).",
    parameters={
        "type": "object",
        "properties": {"task_id": {"type": "string"}},
        "required": ["task_id"],
        "additionalProperties": False,
    },
    tags=["write", "tasks"],
)
async def delete_task(*, session: AsyncSession, ctx: CallContext, task_id: str) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    ok = await task_service.delete_task(session, parse_uuid(task_id), ws_id)
    if not ok:
        raise ValueError(f"Task {task_id} not found")
    return {"deleted": True}


@tool(
    name="add_subtask",
    description="Add a subtask (checklist item) to an existing task.",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "title": {"type": "string"},
        },
        "required": ["task_id", "title"],
        "additionalProperties": False,
    },
    tags=["write", "tasks"],
)
async def add_subtask(*, session: AsyncSession, ctx: CallContext, task_id: str, title: str) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    from app.schemas.subtask import SubtaskCreate

    sub = await subtask_service.create_subtask(session, parse_uuid(task_id), ws_id, SubtaskCreate(title=title))
    if sub is None:
        raise ValueError(f"Task {task_id} not found")
    return {"id": str(sub.id), "title": sub.title, "is_done": sub.is_done}


@tool(
    name="toggle_subtask",
    description="Mark a subtask done or not done.",
    parameters={
        "type": "object",
        "properties": {
            "subtask_id": {"type": "string"},
            "is_done": {"type": "boolean"},
        },
        "required": ["subtask_id", "is_done"],
        "additionalProperties": False,
    },
    tags=["write", "tasks"],
)
async def toggle_subtask(*, session: AsyncSession, ctx: CallContext, subtask_id: str, is_done: bool) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    from app.schemas.subtask import SubtaskUpdate

    sub = await subtask_service.update_subtask(session, parse_uuid(subtask_id), ws_id, SubtaskUpdate(is_done=is_done))
    if sub is None:
        raise ValueError(f"Subtask {subtask_id} not found")
    return {"id": str(sub.id), "title": sub.title, "is_done": sub.is_done}
