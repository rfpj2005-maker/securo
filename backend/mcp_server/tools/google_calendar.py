from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.google_calendar import CalendarEventCreate, CalendarEventUpdate
from app.services import google_calendar_service as gcal
from mcp_server.auth import CallContext
from mcp_server.registry import tool


async def _require_connection(session: AsyncSession, ctx: CallContext):
    conn = await gcal.get_connection(session, ctx.user_id)
    if conn is None:
        raise ValueError("Google Calendar is not connected. Ask the user to connect it on the /calendar page first.")
    return conn


@tool(
    name="list_calendar_events",
    description="List the user's Google Calendar events in a date range, merged across all of their calendars. Defaults to the next 30 days. Each item includes calendar_id/calendar_summary — pass calendar_id back to update_calendar_event/delete_calendar_event.",
    parameters={
        "type": "object",
        "properties": {
            "start": {"type": "string", "format": "date-time", "description": "ISO 8601, defaults to now"},
            "end": {"type": "string", "format": "date-time", "description": "ISO 8601, defaults to 30 days from now"},
        },
        "additionalProperties": False,
    },
    tags=["read", "calendar"],
)
async def list_calendar_events(
    *, session: AsyncSession, ctx: CallContext, start: str | None = None, end: str | None = None
) -> dict[str, Any]:
    conn = await _require_connection(session, ctx)
    now = datetime.now(timezone.utc)
    time_min = datetime.fromisoformat(start) if start else now
    time_max = datetime.fromisoformat(end) if end else now + timedelta(days=30)
    events = await gcal.list_events(session, conn, time_min=time_min, time_max=time_max)
    return {"items": events, "total": len(events)}


@tool(
    name="create_calendar_event",
    description="Create a new event on the user's Google Calendar.",
    parameters={
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Event title"},
            "start": {"type": "string", "format": "date-time", "description": "ISO 8601 start"},
            "end": {"type": "string", "format": "date-time", "description": "ISO 8601 end"},
            "description": {"type": "string"},
            "location": {"type": "string"},
            "all_day": {"type": "boolean", "default": False},
        },
        "required": ["summary", "start", "end"],
        "additionalProperties": False,
    },
    tags=["write", "calendar"],
)
async def create_calendar_event(
    *,
    session: AsyncSession,
    ctx: CallContext,
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    all_day: bool = False,
) -> dict[str, Any]:
    conn = await _require_connection(session, ctx)
    data = CalendarEventCreate(
        summary=summary,
        description=description,
        location=location,
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
        all_day=all_day,
    )
    return await gcal.create_event(session, conn, data)


@tool(
    name="update_calendar_event",
    description="Update an existing Google Calendar event. calendar_id comes from list_calendar_events.",
    parameters={
        "type": "object",
        "properties": {
            "event_id": {"type": "string"},
            "calendar_id": {"type": "string", "description": "From the event's calendar_id, as returned by list_calendar_events"},
            "summary": {"type": "string"},
            "start": {"type": "string", "format": "date-time"},
            "end": {"type": "string", "format": "date-time"},
            "description": {"type": "string"},
            "location": {"type": "string"},
            "all_day": {"type": "boolean"},
        },
        "required": ["event_id", "calendar_id"],
        "additionalProperties": False,
    },
    tags=["write", "calendar"],
)
async def update_calendar_event(
    *,
    session: AsyncSession,
    ctx: CallContext,
    event_id: str,
    calendar_id: str,
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
    all_day: bool | None = None,
) -> dict[str, Any]:
    conn = await _require_connection(session, ctx)
    data = CalendarEventUpdate(
        summary=summary,
        description=description,
        location=location,
        start=datetime.fromisoformat(start) if start else None,
        end=datetime.fromisoformat(end) if end else None,
        all_day=all_day,
    )
    return await gcal.update_event(session, conn, calendar_id, event_id, data)


@tool(
    name="delete_calendar_event",
    description="Delete a Google Calendar event. calendar_id comes from list_calendar_events.",
    parameters={
        "type": "object",
        "properties": {
            "event_id": {"type": "string"},
            "calendar_id": {"type": "string", "description": "From the event's calendar_id, as returned by list_calendar_events"},
        },
        "required": ["event_id", "calendar_id"],
        "additionalProperties": False,
    },
    tags=["write", "calendar"],
)
async def delete_calendar_event(*, session: AsyncSession, ctx: CallContext, event_id: str, calendar_id: str) -> dict[str, Any]:
    conn = await _require_connection(session, ctx)
    await gcal.delete_event(session, conn, calendar_id, event_id)
    return {"deleted": True}
