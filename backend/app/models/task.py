import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.subtask import Subtask


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(20), default="administrative")  # marketing, management, commercial, administrative
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Time-of-day component for the due date — optional. When set, the
    # reminder fires at this exact time (in the user's own timezone); when
    # null, the reminder task falls back to a default hour. Meaningless
    # without a due_date.
    due_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, completed
    # Free-text notes/observações — optional context that doesn't fit in
    # the title (a contact, a link, extra instructions).
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Set once the due-date push reminder has fired, so the periodic
    # reminder job never notifies the same task twice. Cleared automatically
    # whenever due_date/due_time changes (see task_service.update_task).
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Recurrence — null means "does not repeat". When set, the periodic
    # reminder job (task_reminder_tasks.py) rolls due_date forward by
    # recurrence_interval * recurrence_frequency once it's in the past,
    # resetting status to pending and reminder_sent_at to null so the task
    # behaves like a fresh occurrence (e.g. a daily medication reminder).
    recurrence_frequency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # daily, weekly, monthly, yearly
    recurrence_interval: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    recurrence_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Set when a task was auto-created from a meeting's action items. Nullable —
    # most tasks aren't meeting-sourced. ON DELETE SET NULL so removing the
    # meeting recording keeps the task, just detaches its origin.
    source_meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    subtasks: Mapped[list["Subtask"]] = relationship(
        back_populates="task", order_by="Subtask.position", cascade="all, delete-orphan"
    )
