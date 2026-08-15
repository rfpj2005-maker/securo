"""add task_subtasks table

Revision ID: 067
Revises: 066
Create Date: 2026-08-14

Sub-checklist items inside a Task, so a to-do can be broken into smaller
steps (e.g. "Criar checklist do ADM" -> "Levantar etapas", "Revisar com
o Davi"). Workspace-scoped like every other domain table, cascades on
task deletion.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "067"
down_revision: Union[str, None] = "066"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_subtasks",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_subtasks_workspace_id", "task_subtasks", ["workspace_id"])
    op.create_index("ix_task_subtasks_task_id", "task_subtasks", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_task_subtasks_task_id", table_name="task_subtasks")
    op.drop_index("ix_task_subtasks_workspace_id", table_name="task_subtasks")
    op.drop_table("task_subtasks")
