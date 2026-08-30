"""add chat attachments

Revision ID: 084
Revises: 083
Create Date: 2026-08-30

Lets a user attach photos/PDFs to a chat message. Uploaded files land in
`agent_chat_attachments` (bytes on disk, row holds metadata) via a
dedicated upload endpoint that returns an id; sending a message then
references those ids. `agent_messages.attachments` stores which ones
ended up on a given persisted message, so history replay can reload the
bytes and resend them to the LLM on later turns (the Messages API is
stateless — nothing is remembered provider-side between calls).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "084"
down_revision: Union[str, None] = "083"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_chat_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_chat_attachments_agent_id", "agent_chat_attachments", ["agent_id"])
    op.create_index("ix_agent_chat_attachments_user_id", "agent_chat_attachments", ["user_id"])

    op.add_column("agent_messages", sa.Column("attachments", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_messages", "attachments")
    op.drop_index("ix_agent_chat_attachments_user_id", table_name="agent_chat_attachments")
    op.drop_index("ix_agent_chat_attachments_agent_id", table_name="agent_chat_attachments")
    op.drop_table("agent_chat_attachments")
