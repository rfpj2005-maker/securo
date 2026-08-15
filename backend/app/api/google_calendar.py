from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.user import User
from app.schemas.google_calendar import (
    CalendarEventCreate,
    CalendarEventRead,
    CalendarEventUpdate,
    GoogleCalendarInfo,
    GoogleCalendarSelect,
    GoogleCalendarStatus,
)
from app.services import google_calendar_service as gcal

router = APIRouter(prefix="/api/integrations/google-calendar", tags=["google-calendar"])


async def _require_connection(session: AsyncSession, user: User):
    conn = await gcal.get_connection(session, user.id)
    if conn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Google Calendar not connected")
    return conn


@router.get("/status", response_model=GoogleCalendarStatus)
async def status_(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await gcal.get_connection(session, user.id)
    if conn is None:
        return GoogleCalendarStatus(connected=False)
    return GoogleCalendarStatus(
        connected=True, google_email=conn.google_email, selected_calendar_id=conn.selected_calendar_id
    )


@router.get("/connect")
async def connect(user: User = Depends(current_active_user)):
    try:
        url = gcal.build_authorize_url(user.id)
    except gcal.GoogleCalendarNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"authorize_url": url}


@router.get("/callback")
async def callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    frontend_url = get_settings().frontend_url.rstrip("/")
    if error or not code or not state:
        return RedirectResponse(f"{frontend_url}/calendar?google_calendar_error=1")
    try:
        user_id = gcal.verify_state(state)
        await gcal.exchange_code(session, user_id, code)
    except Exception:
        return RedirectResponse(f"{frontend_url}/calendar?google_calendar_error=1")
    return RedirectResponse(f"{frontend_url}/calendar?google_calendar_connected=1")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    await gcal.disconnect(session, user.id)


@router.get("/calendars", response_model=list[GoogleCalendarInfo])
async def calendars(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    try:
        return await gcal.list_calendars(session, conn)
    except gcal.GoogleCalendarNotConnected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/select", response_model=GoogleCalendarStatus)
async def select_calendar(
    data: GoogleCalendarSelect,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await gcal.set_selected_calendar(session, user.id, data.calendar_id)
    if conn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Google Calendar not connected")
    return GoogleCalendarStatus(connected=True, google_email=conn.google_email, selected_calendar_id=conn.selected_calendar_id)


@router.get("/events", response_model=list[CalendarEventRead])
async def list_events(
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    now = datetime.now(timezone.utc)
    time_min = start or (now - timedelta(days=7))
    time_max = end or (now + timedelta(days=60))
    try:
        return await gcal.list_events(session, conn, time_min=time_min, time_max=time_max)
    except gcal.GoogleCalendarNotConnected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/events", response_model=CalendarEventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: CalendarEventCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    return await gcal.create_event(session, conn, data)


@router.patch("/events/{event_id}", response_model=CalendarEventRead)
async def update_event(
    event_id: str,
    data: CalendarEventUpdate,
    calendar_id: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    return await gcal.update_event(session, conn, calendar_id, event_id, data)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    calendar_id: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    await gcal.delete_event(session, conn, calendar_id, event_id)
