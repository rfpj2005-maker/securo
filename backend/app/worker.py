from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "securo",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "sync-all-connections-hourly": {
        "task": "app.tasks.sync_tasks.sync_all_connections",
        "schedule": 60 * 60,  # every hour; task itself skips connections synced < 4h ago
    },
    "generate-recurring-daily": {
        "task": "app.tasks.recurring_tasks.generate_all_recurring",
        "schedule": 60 * 60,  # every hour; generate_pending is idempotent (advances next_occurrence)
    },
    "apply-asset-growth-daily": {
        "task": "app.tasks.asset_tasks.apply_asset_growth_rules",
        "schedule": 60 * 60,  # every hour; idempotent (checks last value date)
    },
    "refresh-market-prices-daily": {
        "task": "app.tasks.asset_tasks.refresh_market_prices",
        # Once a day is enough for personal portfolio tracking — keeps us
        # well under Yahoo's unofficial per-IP caps and avoids the bot
        # heuristics that trip on a chatty schedule. Task upserts today's
        # AssetValue so history stays at one row per day per asset.
        "schedule": 60 * 60 * 24,
    },
    "sync-fx-rates-daily": {
        "task": "app.tasks.fx_rate_tasks.sync_fx_rates",
        "schedule": 60 * 60 * 12,  # twice daily (~60 API calls/month)
    },
    "restamp-recurring-fx-daily": {
        "task": "app.tasks.fx_rate_tasks.restamp_recurring_fx",
        "schedule": 60 * 60 * 12,  # twice daily, after FX rate sync
    },
    "restamp-fallback-fx-daily": {
        "task": "app.tasks.fx_rate_tasks.restamp_fallback_fx",
        # Twice daily, after FX rate sync — heals transactions that were
        # stamped with the 1:1 fallback (or left NULL) once real rates land.
        "schedule": 60 * 60 * 12,
    },
    "check-due-task-reminders": {
        "task": "app.tasks.task_reminder_tasks.check_due_task_reminders",
        # Every minute — a "reminder" that lands minutes late defeats the
        # point. The query is cheap (per-user due-task lookup) and the task
        # itself no-ops instantly if VAPID isn't configured.
        "schedule": 60,
    },
    "check-upcoming-calendar-events": {
        "task": "app.tasks.calendar_reminder_tasks.check_upcoming_calendar_events",
        # Every 5 minutes, not every minute like tasks — this one calls the
        # Google Calendar API per connected user, so keep it cheap on quota.
        # Combined with the 15-minute lookahead in the task itself, a
        # reminder lands ~10-15 minutes before the event.
        "schedule": 60 * 5,
    },
    "sync-siprov-carteira": {
        "task": "app.tasks.siprov_tasks.sync_siprov_carteira",
        # Same cadence already used elsewhere for this exact portfolio pull
        # (Painel Amparar's negativados sync) — frequent enough that the
        # local cache is never far behind, without hammering Siprov's auth
        # endpoint (which rate-limits aggressively on back-to-back calls).
        "schedule": 60 * 60 * 6,
    },
}

celery_app.conf.include = [
    "app.tasks.sync_tasks",
    "app.tasks.recurring_tasks",
    "app.tasks.asset_tasks",
    "app.tasks.fx_rate_tasks",
    "app.tasks.meeting_tasks",
    "app.tasks.task_reminder_tasks",
    "app.tasks.calendar_reminder_tasks",
    "app.tasks.siprov_tasks",
    # Optional agents module — registering the import is harmless when
    # AGENTS_ENABLED=false (the task just won't be dispatched).
    "app.agents.tasks.ingest",
]
