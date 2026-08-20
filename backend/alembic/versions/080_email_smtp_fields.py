"""add smtp fields to email_connections

Revision ID: 080
Revises: 079
Create Date: 2026-08-17

Phase 4: sending. IMAP only reads — outgoing mail needs SMTP. These are
nullable/optional because most hosts mirror their IMAP hostname with an
"smtp." prefix, so the app derives a default at send time when unset
(see email_imap_service._smtp_host); a user whose provider doesn't follow
that convention can still override it explicitly.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "080"
down_revision: Union[str, None] = "079"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("email_connections", sa.Column("smtp_host", sa.String(length=255), nullable=True))
    op.add_column(
        "email_connections",
        sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="465"),
    )
    op.add_column(
        "email_connections",
        sa.Column("smtp_use_ssl", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("email_connections", "smtp_use_ssl")
    op.drop_column("email_connections", "smtp_port")
    op.drop_column("email_connections", "smtp_host")
