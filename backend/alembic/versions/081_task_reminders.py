"""add due_time and reminder_sent_at to tasks

Revision ID: 081
Revises: 080
Create Date: 2026-08-18

Task reminders: due_time is an optional time-of-day paired with the
existing due_date; reminder_sent_at tracks whether the periodic reminder
job has already notified for this task, so it never double-fires.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "081"
down_revision: Union[str, None] = "080"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("due_time", sa.Time(), nullable=True))
    op.add_column("tasks", sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "reminder_sent_at")
    op.drop_column("tasks", "due_time")
