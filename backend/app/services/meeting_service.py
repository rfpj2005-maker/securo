"""Meeting recordings.

Upload path:
  1. Save raw audio bytes to disk under MEETINGS_AUDIO_STORAGE_PATH.
  2. Insert Meeting with status="pending".
  3. Dispatch Celery task (app/tasks/meeting_tasks.py) to transcribe,
     summarize, and auto-create tasks from the action items — asynchronously.
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.meeting import Meeting
from app.models.task import Task
from app.schemas.meeting import MEETING_TYPES


def _storage_dir() -> str:
    base = get_settings().meetings_audio_storage_path
    os.makedirs(base, exist_ok=True)
    return base


def _disk_path(meeting_id: uuid.UUID, filename: str) -> str:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)[-80:]
    return os.path.join(_storage_dir(), f"{meeting_id}__{safe}")


def _validate_audio(filename: str, size: int) -> None:
    settings = get_settings()
    max_bytes = settings.meetings_audio_max_size_mb * 1024 * 1024
    if size > max_bytes:
        raise ValueError(f"Audio file too large. Maximum size is {settings.meetings_audio_max_size_mb} MB.")
    allowed = {ext.strip().lower() for ext in settings.meetings_audio_allowed_extensions.split(",")}
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed:
        raise ValueError(f"Audio type '.{ext}' is not allowed. Allowed: {', '.join(sorted(allowed))}")


async def create_meeting_with_audio(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    meeting_type: str,
    filename: str,
    payload: bytes,
) -> Meeting:
    if meeting_type not in MEETING_TYPES:
        raise ValueError(f"meeting_type must be one of {MEETING_TYPES}")
    _validate_audio(filename, len(payload))

    meeting = Meeting(
        user_id=user_id,
        workspace_id=workspace_id,
        title=title.strip() or "Reunião",
        meeting_type=meeting_type,
        status="pending",
    )
    session.add(meeting)
    await session.flush()  # need meeting.id to build the disk path

    path = _disk_path(meeting.id, filename)
    with open(path, "wb") as fh:
        fh.write(payload)
    meeting.audio_storage_path = path

    await session.commit()
    await session.refresh(meeting)
    return meeting


async def list_meetings(session: AsyncSession, workspace_id: uuid.UUID) -> list[Meeting]:
    result = await session.execute(
        select(Meeting).where(Meeting.workspace_id == workspace_id).order_by(Meeting.recorded_at.desc())
    )
    return list(result.scalars().all())


async def get_meeting(session: AsyncSession, meeting_id: uuid.UUID, workspace_id: uuid.UUID) -> Optional[Meeting]:
    result = await session.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()


async def get_meeting_tasks(session: AsyncSession, meeting_id: uuid.UUID, workspace_id: uuid.UUID) -> list[Task]:
    result = await session.execute(
        select(Task)
        .where(Task.source_meeting_id == meeting_id, Task.workspace_id == workspace_id)
        .options(selectinload(Task.subtasks))
        .order_by(Task.created_at)
    )
    return list(result.scalars().all())


async def delete_meeting(session: AsyncSession, meeting_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
    meeting = await get_meeting(session, meeting_id, workspace_id)
    if meeting is None:
        return False
    path = meeting.audio_storage_path
    await session.delete(meeting)
    await session.commit()
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    return True


async def mark_status(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    *,
    status: str,
    error: Optional[str] = None,
    transcript: Optional[str] = None,
    summary: Optional[str] = None,
    duration_seconds: Optional[int] = None,
) -> None:
    meeting = (await session.execute(select(Meeting).where(Meeting.id == meeting_id))).scalar_one_or_none()
    if meeting is None:
        return
    meeting.status = status
    # On success, always clear any stale error from a prior failed attempt —
    # otherwise the UI would keep showing "transcription failed: …" next to
    # a completed badge.
    if status == "completed":
        meeting.error = None
    elif error is not None:
        meeting.error = error
    if transcript is not None:
        meeting.transcript = transcript
    if summary is not None:
        meeting.summary = summary
    if duration_seconds is not None:
        meeting.duration_seconds = duration_seconds
    await session.commit()


async def retry_meeting(session: AsyncSession, meeting_id: uuid.UUID, workspace_id: uuid.UUID) -> Optional[Meeting]:
    meeting = await get_meeting(session, meeting_id, workspace_id)
    if meeting is None or not meeting.audio_storage_path:
        return None
    meeting.status = "pending"
    meeting.error = None
    await session.commit()
    await session.refresh(meeting)
    return meeting
