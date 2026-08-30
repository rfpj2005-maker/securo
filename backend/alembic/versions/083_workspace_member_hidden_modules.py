"""add workspace_member_hidden_modules table

Revision ID: 083
Revises: 082
Create Date: 2026-08-23

Per-member overrides on top of what a workspace grants: an owner can hide
specific modules/features from a specific sócio. One row per hidden id;
absence of a row means the member sees whatever the workspace shows.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "083"
down_revision: Union[str, None] = "082"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_member_hidden_modules",
        sa.Column("workspace_member_id", UUID(as_uuid=True), nullable=False),
        sa.Column("module_id", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_member_id"], ["workspace_members.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("workspace_member_id", "module_id"),
    )


def downgrade() -> None:
    op.drop_table("workspace_member_hidden_modules")
