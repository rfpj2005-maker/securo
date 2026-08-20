import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class EmailConnection(Base):
    """One IMAP mailbox linked per user — Hostinger, or any other provider
    that isn't Gmail (no OAuth here, just host/port/username/password like
    a normal mail client). Personal integration like GmailConnection —
    not workspace-scoped."""

    __tablename__ = "email_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    email_address: Mapped[str] = mapped_column(String(255))
    imap_host: Mapped[str] = mapped_column(String(255))
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    imap_use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    username: Mapped[str] = mapped_column(String(255))
    # Fernet ciphertext (base64), same scheme as agent_llm_connections.
    password_encrypted: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # SMTP (sending) — optional. Most hosts mirror their IMAP hostname with
    # an "smtp." prefix, so this is nullable and derived at send time when
    # unset (see email_imap_service._smtp_host). Left here so a user whose
    # provider doesn't follow that convention can override it.
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int] = mapped_column(Integer, default=465)
    smtp_use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
