"""add email_connections table

Revision ID: 079
Revises: 078
Create Date: 2026-08-16

IMAP-based email connections (Hostinger, or any other provider that isn't
Gmail) — no OAuth, just host/port/username/password like a normal mail
client setup. Read-only for now (Phase 2), same as gmail_connections was
for Phase 1. One row per user.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "079"
down_revision: Union[str, None] = "078"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_connections",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("email_address", sa.String(length=255), nullable=False),
        sa.Column("imap_host", sa.String(length=255), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("imap_use_ssl", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_encrypted", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_email_connections_user_id"),
    )


def downgrade() -> None:
    op.drop_table("email_connections")
