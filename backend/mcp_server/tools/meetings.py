from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import meeting_service
from mcp_server.auth import CallContext
from mcp_server.registry import tool
from mcp_server.tools._helpers import parse_uuid, resolve_workspace_id


def _meeting_to_dict(m: Any, *, with_transcript: bool = False) -> dict[str, Any]:
    data = {
        "id": str(m.id),
        "title": m.title,
        "meeting_type": m.meeting_type,
        "status": m.status,
        "error": m.error,
        "duration_seconds": m.duration_seconds,
        "summary": m.summary,
        "recorded_at": m.recorded_at.isoformat() if m.recorded_at else None,
    }
    if with_transcript:
        data["transcript"] = m.transcript
    return data


@tool(
    name="list_meetings",
    description="List the user's recorded meetings (in-person or online), with status, summary, and recording date.",
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    tags=["read", "meetings"],
)
async def list_meetings(*, session: AsyncSession, ctx: CallContext) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    rows = await meeting_service.list_meetings(session, ws_id)
    return {"items": [_meeting_to_dict(m) for m in rows], "total": len(rows)}


@tool(
    name="get_meeting",
    description="Get full details of one meeting, including its transcript, summary, and the tasks auto-created from it.",
    parameters={
        "type": "object",
        "properties": {"meeting_id": {"type": "string"}},
        "required": ["meeting_id"],
        "additionalProperties": False,
    },
    tags=["read", "meetings"],
)
async def get_meeting(*, session: AsyncSession, ctx: CallContext, meeting_id: str) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)
    m = await meeting_service.get_meeting(session, parse_uuid(meeting_id), ws_id)
    if m is None:
        raise ValueError(f"Meeting {meeting_id} not found")
    tasks = await meeting_service.get_meeting_tasks(session, m.id, ws_id)
    data = _meeting_to_dict(m, with_transcript=True)
    data["created_tasks"] = [{"id": str(t.id), "title": t.title, "status": t.status} for t in tasks]
    return data
