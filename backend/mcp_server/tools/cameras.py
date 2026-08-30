from __future__ import annotations

from datetime import date as _date, time as _time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import camera_service
from app.services.workspace_service import is_business_member
from mcp_server.auth import CallContext
from mcp_server.registry import tool


async def _require_business_member(session: AsyncSession, ctx: CallContext) -> None:
    """Cameras are Amparar company infrastructure, not workspace data —
    mirrors the same gate api/cameras.py enforces over HTTP
    (current_business_user). An agent belonging to a personal-only user
    has no business seeing store security footage just because they're
    on this install."""
    if not await is_business_member(session, ctx.user_id):
        raise PermissionError("Cameras are only available to business workspace members.")


@tool(
    name="list_cameras",
    description=(
        "List all of Amparar's security cameras across every location (matriz, belvedere, "
        "varginha, centro) with live online/connected status. Does not return images — use this "
        "to answer 'how many cameras', 'is camera X online', or to find the location/name needed "
        "for list_camera_recordings. Tell the user to open the Câmeras page to actually watch the "
        "live feed or a recording — this tool can't show images/video in chat."
    ),
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    tags=["read", "cameras"],
)
async def list_cameras(*, session: AsyncSession, ctx: CallContext) -> dict[str, Any]:
    await _require_business_member(session, ctx)
    items = await camera_service.list_cameras()
    return {"items": items, "total": len(items)}


@tool(
    name="list_camera_recordings",
    description=(
        "List saved recordings for one camera, most recent first. location/camera_name come from "
        "list_cameras (the 'location' and 'name' fields)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "e.g. 'matriz', 'belvedere', 'varginha'"},
            "camera_name": {"type": "string", "description": "e.g. 'PVBelve02'"},
        },
        "required": ["location", "camera_name"],
        "additionalProperties": False,
    },
    tags=["read", "cameras"],
)
async def list_camera_recordings(
    *, session: AsyncSession, ctx: CallContext, location: str, camera_name: str
) -> dict[str, Any]:
    await _require_business_member(session, ctx)
    items = await camera_service.list_recordings(location, camera_name)
    return {"items": items, "total": len(items)}


@tool(
    name="search_camera_recordings",
    description=(
        "Find recordings for one camera on a specific day and/or time-of-day range — use this "
        "instead of list_camera_recordings whenever the user gives a date, 'today', 'yesterday', "
        "or a time like 'this morning' or 'around 3pm', since a camera can have hundreds of clips "
        "and this filters server-side instead of dumping them all. location/camera_name come from "
        "list_cameras. Still returns metadata only — tell the user to open the Câmeras page to "
        "actually watch a match."
    ),
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "e.g. 'matriz', 'belvedere', 'varginha'"},
            "camera_name": {"type": "string", "description": "e.g. 'PVBelve02'"},
            "date": {"type": "string", "format": "date", "description": "YYYY-MM-DD, optional"},
            "time_from": {"type": "string", "description": "HH:MM, optional — start of the time-of-day window"},
            "time_to": {"type": "string", "description": "HH:MM, optional — end of the time-of-day window"},
        },
        "required": ["location", "camera_name"],
        "additionalProperties": False,
    },
    tags=["read", "cameras"],
)
async def search_camera_recordings(
    *,
    session: AsyncSession,
    ctx: CallContext,
    location: str,
    camera_name: str,
    date: str | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
) -> dict[str, Any]:
    await _require_business_member(session, ctx)
    items = await camera_service.search_recordings(
        location,
        camera_name,
        on_date=_date.fromisoformat(date) if date else None,
        time_from=_time.fromisoformat(time_from) if time_from else None,
        time_to=_time.fromisoformat(time_to) if time_to else None,
    )
    return {"items": items, "total": len(items)}
