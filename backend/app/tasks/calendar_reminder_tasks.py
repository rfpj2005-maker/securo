import asyncio
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.worker import celery_app
from app.core.config import get_settings
from app.models.calendar_event_reminder import CalendarEventReminder
from app.models.google_calendar_connection import GoogleCalendarConnection
from app.models.user import User
from app.services import google_calendar_service as gcal
from app.services import push_service

logger = logging.getLogger(__name__)

# How far ahead to look for upcoming events. Polling every 5 minutes (see
# worker.py's beat schedule) with a 15-minute lookahead means a reminder
# lands somewhere between ~10 and ~15 minutes before the event starts.
_LOOKAHEAD_MINUTES = 15


def _make_session_maker():
    """Create a fresh engine+session for the Celery worker event loop."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _already_notified(session: AsyncSession, user_id, event_id: str) -> bool:
    result = await session.execute(
        select(CalendarEventReminder.id).where(
            CalendarEventReminder.user_id == user_id, CalendarEventReminder.event_id == event_id
        )
    )
    return result.scalar_one_or_none() is not None


async def _check_all() -> int:
    """Push a reminder for every Google Calendar event starting within the
    next _LOOKAHEAD_MINUTES minutes, for every user with a connected
    calendar. One user's revoked token / API error never blocks another's."""
    settings = get_settings()
    if not settings.vapid_private_key.get_secret_value() or not settings.vapid_claim_email:
        return 0  # push not configured for this deployment — nothing to do

    engine, session_maker = _make_session_maker()
    notified = 0
    try:
        async with session_maker() as session:
            rows = (
                await session.execute(
                    select(GoogleCalendarConnection.user_id, User.preferences).join(
                        User, User.id == GoogleCalendarConnection.user_id
                    )
                )
            ).all()

        now_utc = datetime.now(dt_timezone.utc)
        window_end = now_utc + timedelta(minutes=_LOOKAHEAD_MINUTES)

        for user_id, preferences in rows:
            tz_name = (preferences or {}).get("timezone") or "UTC"
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = ZoneInfo("UTC")

            try:
                async with session_maker() as session:
                    conn = await gcal.get_connection(session, user_id)
                    if conn is None:
                        continue
                    events = await gcal.list_events(session, conn, time_min=now_utc, time_max=window_end)
                    for ev in events:
                        if ev.get("all_day"):
                            continue  # no specific time to count down to
                        start_raw = ev.get("start")
                        if not start_raw:
                            continue
                        try:
                            start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                        except ValueError:
                            continue
                        if start_dt.tzinfo is None:
                            start_dt = start_dt.replace(tzinfo=dt_timezone.utc)
                        if start_dt < now_utc or start_dt > window_end:
                            continue
                        if await _already_notified(session, user_id, ev["id"]):
                            continue
                        start_local = start_dt.astimezone(tz)
                        sent = await push_service.notify_user(
                            session,
                            user_id,
                            title="Compromisso em breve",
                            body=f"{ev.get('summary') or '(sem título)'} às {start_local.strftime('%H:%M')}",
                            url="/calendar",
                        )
                        session.add(CalendarEventReminder(user_id=user_id, event_id=ev["id"]))
                        await session.commit()
                        if sent:
                            notified += 1
            except Exception:
                logger.exception("Failed checking calendar reminders for user %s", user_id)
    finally:
        await engine.dispose()
    return notified


@celery_app.task(name="app.tasks.calendar_reminder_tasks.check_upcoming_calendar_events")
def check_upcoming_calendar_events() -> dict:
    """Celery task: push a reminder for every calendar event starting soon."""
    notified = asyncio.run(_check_all())
    if notified:
        logger.info("Calendar reminders sent: %d", notified)
    return {"notified": notified}
