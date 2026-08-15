"""Celery task: transcribe a meeting recording, summarize it, and turn the
action items into real Tasks.

Pipeline (app/services/meeting_service.py tracks status through each step):
  1. transcribing — faster-whisper decodes + transcribes the audio on CPU,
     entirely inside this worker process. No audio ever leaves the server.
  2. summarizing  — the transcript is sent to the user's default agents LLM
     connection (same one the chat assistant uses) to produce a short
     summary and a list of action items.
  3. completed    — action items are inserted as real Tasks, tagged with
     source_meeting_id so the meeting page can show what it created.

Registered with the existing celery_app. Dispatched from the upload endpoint
via celery_app.send_task (see app/api/meetings.py) rather than imported
directly, so the (heavy) faster-whisper import only ever happens inside the
celery-worker process, never in the web/uvicorn process.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.worker import celery_app

logger = logging.getLogger(__name__)

_whisper_model = None  # lazily loaded once per worker process


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        settings = get_settings()
        _whisper_model = WhisperModel(
            settings.meetings_whisper_model,
            device=settings.meetings_whisper_device,
            compute_type=settings.meetings_whisper_compute_type,
            download_root=settings.meetings_whisper_model_path,
        )
    return _whisper_model


def _transcribe(audio_path: str) -> tuple[str, float]:
    """Blocking, CPU-bound. Always called via asyncio.to_thread."""
    model = _get_whisper_model()
    segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)
    parts = [seg.text.strip() for seg in segments if seg.text.strip()]
    return " ".join(parts), float(info.duration or 0)


_SUMMARY_PROMPT = """You are analyzing the transcript of a meeting (in-person or online). Read it and produce a structured summary.

Respond with ONLY a JSON object — no markdown fences, no commentary before or after — in exactly this shape:
{{
  "summary": "a concise summary of what was discussed and decided, 3-6 sentences, written in the SAME language as the transcript",
  "action_items": [
    {{"title": "a specific, actionable task title, written in the SAME language as the transcript", "due_date": "YYYY-MM-DD if a deadline was clearly mentioned, otherwise null"}}
  ]
}}

Only include action items explicitly stated or clearly implied in the transcript — never invent tasks that weren't discussed. If there are none, use an empty array.

Transcript:
{transcript}
"""

_MAX_TRANSCRIPT_CHARS = 100_000


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _parse_due_date(value: Any) -> Optional[date]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


@celery_app.task(name="app.tasks.meeting_tasks.process_meeting", bind=True, max_retries=1, default_retry_delay=30)
def process_meeting(self, meeting_id_str: str) -> dict:
    """Sync entry point that runs the async pipeline in a fresh loop."""
    return asyncio.run(_async_process(meeting_id_str))


async def _async_process(meeting_id_str: str) -> dict:
    meeting_id = uuid.UUID(meeting_id_str)
    # Fresh engine per task — reusing the global session maker inside Celery
    # prefork workers reuses asyncpg connections bound to event loops that
    # asyncio.run() has already closed, raising "another operation is in
    # progress" on the next task (same fix as app/agents/tasks/ingest.py).
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        return await _do_process(session_maker, meeting_id)
    finally:
        await engine.dispose()


async def _do_process(session_maker, meeting_id: uuid.UUID) -> dict:
    from sqlalchemy import select

    from app.agents.providers.base import ChatMessage
    from app.agents.services import connection_service
    from app.models.meeting import Meeting
    from app.schemas.task import TaskCreate
    from app.services import meeting_service, task_service

    async with session_maker() as session:
        meeting = (await session.execute(select(Meeting).where(Meeting.id == meeting_id))).scalar_one_or_none()
        if meeting is None or not meeting.audio_storage_path:
            return {"ok": False, "reason": "meeting missing"}

        await meeting_service.mark_status(session, meeting_id, status="transcribing")

        try:
            transcript, duration = await asyncio.to_thread(_transcribe, meeting.audio_storage_path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("transcription failed for meeting %s", meeting_id)
            await meeting_service.mark_status(session, meeting_id, status="failed", error=f"Transcription failed: {exc}")
            return {"ok": False, "reason": "transcription failed"}

        if not transcript.strip():
            await meeting_service.mark_status(
                session, meeting_id, status="failed", error="No speech was detected in the recording.",
                duration_seconds=int(duration),
            )
            return {"ok": False, "reason": "empty transcript"}

        await meeting_service.mark_status(
            session, meeting_id, status="summarizing", transcript=transcript, duration_seconds=int(duration)
        )

        conn = await connection_service.get_default_connection(session, meeting.user_id)
        if conn is None:
            await meeting_service.mark_status(
                session, meeting_id, status="completed",
                error="Transcription finished, but no default AI connection is configured, so no summary or tasks were generated. Set one up under AI agents → Connections.",
            )
            return {"ok": True, "summary": False}

        provider = connection_service.build_provider_for_connection(conn)
        prompt = _SUMMARY_PROMPT.format(transcript=transcript[:_MAX_TRANSCRIPT_CHARS])
        try:
            response = await provider.chat(
                [ChatMessage(role="user", content=prompt)],
                model=conn.default_model or "",
                temperature=0.3,
                max_tokens=2000,
            )
            parsed = _extract_json(response.content or "")
        except Exception as exc:  # noqa: BLE001
            logger.exception("summarization failed for meeting %s", meeting_id)
            await meeting_service.mark_status(
                session, meeting_id, status="completed",
                error=f"Transcription finished, but summarization failed: {exc}",
            )
            return {"ok": True, "summary": False}

        summary = str(parsed.get("summary") or "").strip()
        action_items = parsed.get("action_items") or []

        created = 0
        for item in action_items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            task = await task_service.create_task(
                session,
                meeting.workspace_id,
                meeting.user_id,
                TaskCreate(title=title, category="meetings", due_date=_parse_due_date(item.get("due_date"))),
            )
            task.source_meeting_id = meeting_id
            created += 1
        if created:
            await session.commit()

        await meeting_service.mark_status(session, meeting_id, status="completed", summary=summary or None)
        return {"ok": True, "summary": True, "tasks_created": created}
