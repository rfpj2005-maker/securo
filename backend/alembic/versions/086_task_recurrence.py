"""add recurrence fields to tasks

Revision ID: 086
Revises: 085
Create Date: 2026-09-20

Lets a task repeat (daily/weekly/monthly/yearly, every N) from its
due_date — e.g. a daily medication reminder. recurrence_frequency null
means "does not repeat"; task_reminder_tasks.py advances due_date forward
once it's past, so the task behaves like a fresh occurrence each cycle.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "086"
down_revision: Union[str, None] = "085"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("recurrence_frequency", sa.String(length=10), nullable=True))
    op.add_column(
        "tasks",
        sa.Column("recurrence_interval", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("tasks", sa.Column("recurrence_end_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "recurrence_end_date")
    op.drop_column("tasks", "recurrence_interval")
    op.drop_column("tasks", "recurrence_frequency")
