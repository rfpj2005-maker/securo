"""add calendar_event_reminders table

Revision ID: 087
Revises: 086
Create Date: 2026-09-20

Dedup table for calendar_reminder_tasks.py: one row per (user, Google
event id) already pushed, since Google Calendar events aren't stored
locally and the periodic check would otherwise re-notify every poll.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "087"
down_revision: Union[str, None] = "086"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calendar_event_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.String(length=512), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "event_id", name="uq_calendar_event_reminder"),
    )
    op.create_index("ix_calendar_event_reminders_user_id", "calendar_event_reminders", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_calendar_event_reminders_user_id", table_name="calendar_event_reminders")
    op.drop_table("calendar_event_reminders")
