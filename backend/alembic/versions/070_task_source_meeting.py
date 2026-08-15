"""add tasks.source_meeting_id

Revision ID: 070
Revises: 069
Create Date: 2026-08-15

Links a task to the meeting it was auto-created from (Celery summary step).
Nullable — most tasks aren't meeting-sourced. ON DELETE SET NULL so deleting
the meeting recording keeps the task, just detaches its origin.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "070"
down_revision: Union[str, None] = "069"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("source_meeting_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_tasks_source_meeting_id",
        "tasks",
        "meetings",
        ["source_meeting_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_tasks_source_meeting_id", "tasks", ["source_meeting_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_source_meeting_id", table_name="tasks")
    op.drop_constraint("fk_tasks_source_meeting_id", "tasks", type_="foreignkey")
    op.drop_column("tasks", "source_meeting_id")
