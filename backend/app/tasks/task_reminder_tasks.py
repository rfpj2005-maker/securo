import asyncio
import logging
from datetime import datetime, time as dtime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.worker import celery_app
from app.core.config import get_settings
from app.models.task import Task
from app.models.user import User
from app.services import push_service
from app.services.task_recurrence import advance_past_due

logger = logging.getLogger(__name__)

# When a task has no due_time, remind at this local hour instead of at
# midnight (which would fire while the user is presumably asleep).
_DEFAULT_REMINDER_TIME = dtime(8, 0)


def _make_session_maker():
    """Create a fresh engine+session for the Celery worker event loop."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _check_all() -> int:
    """Push a reminder for every pending task whose due date/time has
    arrived (in the owning user's own timezone) and hasn't been notified
    yet. One user's dead/misconfigured subscriptions never block another's."""
    settings = get_settings()
    if not settings.vapid_private_key.get_secret_value() or not settings.vapid_claim_email:
        return 0  # push not configured for this deployment — nothing to do

    engine, session_maker = _make_session_maker()
    notified = 0
    try:
        async with session_maker() as session:
            users = (await session.execute(select(User.id, User.preferences))).all()

        now_utc = datetime.now(dt_timezone.utc)

        for user_id, preferences in users:
            tz_name = (preferences or {}).get("timezone") or "UTC"
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = ZoneInfo("UTC")
            now_local = now_utc.astimezone(tz)

            try:
                async with session_maker() as session:
                    # Roll forward any recurring task whose occurrence date is
                    # already in the past (whether it was completed or just
                    # missed) — regardless of status, since a completed
                    # recurring task (yesterday's dose taken) still needs
                    # tomorrow's occurrence queued up.
                    recurring_past_due = (
                        (
                            await session.execute(
                                select(Task).where(
                                    Task.user_id == user_id,
                                    Task.recurrence_frequency.isnot(None),
                                    Task.due_date != None,  # noqa: E711
                                    Task.due_date < now_local.date(),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    if recurring_past_due:
                        for task in recurring_past_due:
                            advance_past_due(task, now_local.date())
                        await session.commit()

                    due_tasks = (
                        (
                            await session.execute(
                                select(Task).where(
                                    Task.user_id == user_id,
                                    Task.status == "pending",
                                    Task.due_date != None,  # noqa: E711
                                    Task.due_date <= now_local.date(),
                                    Task.reminder_sent_at.is_(None),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    for task in due_tasks:
                        due_local = datetime.combine(task.due_date, task.due_time or _DEFAULT_REMINDER_TIME, tzinfo=tz)
                        if due_local > now_local:
                            continue  # due today, but not until later
                        sent = await push_service.notify_user(
                            session, user_id, title="Tarefa vencendo", body=task.title, url="/tasks"
                        )
                        task.reminder_sent_at = now_utc
                        await session.commit()
                        if sent:
                            notified += 1
            except Exception:
                logger.exception("Failed checking task reminders for user %s", user_id)
    finally:
        await engine.dispose()
    return notified


@celery_app.task(name="app.tasks.task_reminder_tasks.check_due_task_reminders")
def check_due_task_reminders() -> dict:
    """Celery task: push a reminder for every task that just became due."""
    notified = asyncio.run(_check_all())
    if notified:
        logger.info("Task reminders sent: %d", notified)
    return {"notified": notified}
