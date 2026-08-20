"""add gmail_connections table

Revision ID: 075
Revises: 074
Create Date: 2026-08-16

Stores the OAuth2 tokens for a user's linked Gmail account, read-only to
start (Phase 1: search + read). Personal integration, one row per user —
same shape as google_calendar_connections, deliberately a separate table
rather than widening that one, since a user may want Calendar without
Gmail or vice versa, and the two token grants have different scopes.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "075"
down_revision: Union[str, None] = "074"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gmail_connections",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("gmail_email", sa.String(length=255), nullable=True),
        sa.Column("access_token_encrypted", sa.String(length=2000), nullable=True),
        sa.Column("refresh_token_encrypted", sa.String(length=2000), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_gmail_connections_user_id"),
    )


def downgrade() -> None:
    op.drop_table("gmail_connections")
