"""add meetings table

Revision ID: 069
Revises: 068
Create Date: 2026-08-15

Meeting recordings (in-person or online): raw audio on disk, transcript and
AI-generated summary produced by a Celery pipeline (app/tasks/meeting_tasks.py).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "069"
down_revision: Union[str, None] = "068"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("meeting_type", sa.String(length=20), nullable=False, server_default="in_person"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("audio_storage_path", sa.String(length=500), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meetings_workspace_id", "meetings", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_meetings_workspace_id", table_name="meetings")
    op.drop_table("meetings")
