"""Chat message attachments (photos/PDFs).

Upload path:
  1. Save raw bytes to disk under AGENTS_CHAT_ATTACHMENTS_STORAGE_PATH.
  2. Insert a ChatAttachment row with metadata (not the bytes).
The frontend uploads a file the moment it's picked, gets back an id, and
sends that id alongside the message. The executor reloads the bytes from
disk (base64-encoded) both for the turn that attached them and for every
later turn that replays this message from history — the LLM API is
stateless, nothing is remembered provider-side between calls.
"""
from __future__ import annotations

import base64
import os
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.config import get_agent_settings
from app.agents.models.conversation import ChatAttachment

# Kept intentionally narrow: these are the types Claude's Messages API
# understands natively (image content blocks + PDF document blocks).
# Anything else gets a clear "unsupported file type" instead of silently
# reaching the LLM as an opaque blob it can't read.
ALLOWED_MIME = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "application/pdf",
}


def _storage_dir() -> str:
    base = get_agent_settings().chat_attachments_storage_path
    os.makedirs(base, exist_ok=True)
    return base


def _disk_path(attachment_id: uuid.UUID, filename: str) -> str:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)[-80:]
    return os.path.join(_storage_dir(), f"{attachment_id}__{safe}")


async def save_attachment(
    session: AsyncSession,
    *,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
    mime: str,
    payload: bytes,
) -> ChatAttachment:
    if mime not in ALLOWED_MIME:
        raise ValueError(f"unsupported file type: {mime or 'unknown'}. Aceitos: fotos (PNG/JPEG/WEBP/GIF) e PDF.")
    settings = get_agent_settings()
    if len(payload) > settings.chat_attachment_max_file_size_mb * 1024 * 1024:
        raise ValueError(f"file exceeds {settings.chat_attachment_max_file_size_mb} MB limit")

    att = ChatAttachment(
        agent_id=agent_id,
        user_id=user_id,
        filename=filename,
        mime=mime,
        size_bytes=len(payload),
    )
    session.add(att)
    await session.flush()  # need att.id to build the disk path
    path = _disk_path(att.id, filename)
    with open(path, "wb") as fh:
        fh.write(payload)
    att.storage_path = path
    await session.commit()
    await session.refresh(att)
    return att


async def get_attachment(
    session: AsyncSession, attachment_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[ChatAttachment]:
    return (await session.execute(
        select(ChatAttachment).where(ChatAttachment.id == attachment_id, ChatAttachment.user_id == user_id)
    )).scalar_one_or_none()


async def get_attachment_any_owner(session: AsyncSession, attachment_id: uuid.UUID) -> Optional[ChatAttachment]:
    """Unscoped lookup for history replay: the message that references
    this attachment may be read back by anyone with access to the
    conversation, not just the original uploader (a viewer's teammate
    reading a shared workspace conversation, for instance)."""
    return await session.get(ChatAttachment, attachment_id)


def read_bytes(att: ChatAttachment) -> bytes:
    if not att.storage_path or not os.path.exists(att.storage_path):
        raise FileNotFoundError(f"attachment file missing on disk: {att.id}")
    with open(att.storage_path, "rb") as fh:
        return fh.read()


def to_meta(att: ChatAttachment) -> dict[str, Any]:
    """Small dict persisted on the Message row — no bytes, just enough
    to look the file back up (and show a filename/size chip)."""
    return {"id": str(att.id), "filename": att.filename, "mime": att.mime, "size_bytes": att.size_bytes}


def to_llm_attachment(att: ChatAttachment) -> dict[str, str]:
    """Base64-encoded form handed to ChatMessage.attachments for the
    provider to embed as an image/document content block."""
    return {"mime": att.mime, "data_b64": base64.b64encode(read_bytes(att)).decode("ascii")}


async def delete_attachment(session: AsyncSession, attachment_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    att = await get_attachment(session, attachment_id, user_id)
    if att is None:
        return False
    path = att.storage_path
    await session.delete(att)
    await session.commit()
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    return True
