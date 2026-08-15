"""add google_calendar_connections table

Revision ID: 072
Revises: 071
Create Date: 2026-08-14

Stores the OAuth2 tokens for a user's linked Google account, so Securo can
show/create/edit their Google Calendar events. Personal integration (one
row per user), not workspace-scoped — mirrors agent_llm_connections.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "072"
down_revision: Union[str, None] = "071"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "google_calendar_connections",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("google_email", sa.String(length=255), nullable=True),
        sa.Column("access_token_encrypted", sa.String(length=2000), nullable=True),
        sa.Column("refresh_token_encrypted", sa.String(length=2000), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("selected_calendar_id", sa.String(length=255), nullable=False, server_default="primary"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_google_calendar_connections_user_id"),
    )


def downgrade() -> None:
    op.drop_table("google_calendar_connections")
