import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class CalendarEventReminder(Base):
    """Dedup marker: one row per (user, Google event) we've already pushed
    a reminder for. Google Calendar events aren't stored locally, so this
    is the only record that a given occurrence was already notified —
    without it the periodic check (calendar_reminder_tasks.py) would
    re-notify the same event every time it polls."""

    __tablename__ = "calendar_event_reminders"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_calendar_event_reminder"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[str] = mapped_column(String(512))
    notified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
