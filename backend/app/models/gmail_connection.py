import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class GmailConnection(Base):
    """One Gmail account linked per user (OAuth2, offline access for a
    refresh token). Personal integration like GoogleCalendarConnection —
    not workspace-scoped, since a Gmail account belongs to the person."""

    __tablename__ = "gmail_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    gmail_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Fernet ciphertext (base64), same scheme as agent_llm_connections.
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
