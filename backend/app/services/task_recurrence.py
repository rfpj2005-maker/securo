import calendar
from datetime import date, timedelta


def _advance_months(current: date, months: int) -> date:
    """Advance by calendar months, clamping the day to the target month's
    length (e.g. Jan 31 + 1 month -> Feb 28/29)."""
    month_index = current.month - 1 + months
    year = current.year + month_index // 12
    month = month_index % 12 + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_occurrence(current: date, frequency: str, interval: int) -> date:
    if frequency == "daily":
        return current + timedelta(days=interval)
    if frequency == "weekly":
        return current + timedelta(weeks=interval)
    if frequency == "monthly":
        return _advance_months(current, interval)
    if frequency == "yearly":
        return _advance_months(current, interval * 12)
    raise ValueError(f"unknown recurrence frequency: {frequency}")


def advance_past_due(task, today: date, max_steps: int = 1000) -> bool:
    """Roll a recurring task's due_date forward until it's today or later.

    Mutates `task` in place (due_date, status, reminder_sent_at) and
    returns True if anything changed. If the next occurrence would fall
    after recurrence_end_date, recurrence is turned off instead (the task
    keeps its last due_date/status as history) rather than looping forever.
    Works for both a still-pending task (missed day rolls to today) and a
    completed one (today's dose was taken, tomorrow's reminder is queued).
    """
    if not task.recurrence_frequency or task.due_date is None or task.due_date >= today:
        return False
    advanced = False
    for _ in range(max_steps):
        nxt = next_occurrence(task.due_date, task.recurrence_frequency, task.recurrence_interval)
        if task.recurrence_end_date and nxt > task.recurrence_end_date:
            # Recurrence has run its course — stop repeating, but leave the
            # last real occurrence (due_date/status) as history rather than
            # manufacturing one more reminder for a date past the end.
            task.recurrence_frequency = None
            return True
        task.due_date = nxt
        advanced = True
        if nxt >= today:
            break
    if advanced:
        task.status = "pending"
        task.reminder_sent_at = None
    return advanced
