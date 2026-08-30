"""Chat message attachments — upload a photo/PDF, get back an id to send
alongside a chat message. See app.agents.services.attachment_service for
storage details and app.agents.runtime.executor for how the id is turned
into an image/document content block for the LLM.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.services import agent_service, attachment_service
from app.core.database import get_async_session
from app.core.workspace_context import (
    WorkspaceContext,
    current_workspace,
    current_writable_workspace,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _serialize(att) -> dict[str, Any]:
    return {
        "id": str(att.id),
        "agent_id": str(att.agent_id),
        "filename": att.filename,
        "mime": att.mime,
        "size_bytes": att.size_bytes,
        "created_at": att.created_at.isoformat() if att.created_at else None,
    }


@router.post("/{agent_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    agent_id: uuid.UUID,
    file: UploadFile = File(...),
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    agent = await agent_service.get_agent(session, agent_id, ctx.workspace.id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    payload = await file.read()
    try:
        att = await attachment_service.save_attachment(
            session,
            agent_id=agent_id,
            user_id=ctx.user_id,
            filename=file.filename or "arquivo",
            mime=file.content_type or "application/octet-stream",
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    return _serialize(att)


@router.get("/{agent_id}/attachments/{attachment_id}")
async def download_attachment(
    agent_id: uuid.UUID,
    attachment_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Serves the raw bytes back — used by the UI to render a thumbnail
    for an attachment already sent (its own, or a teammate's in a shared
    workspace conversation)."""
    agent = await agent_service.get_agent(session, agent_id, ctx.workspace.id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    att = await attachment_service.get_attachment_any_owner(session, attachment_id)
    if att is None or att.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="attachment not found")
    try:
        data = attachment_service.read_bytes(att)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=data, media_type=att.mime)


@router.delete("/{agent_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    agent_id: uuid.UUID,
    attachment_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Only removes a staged-but-unsent attachment (the uploader's own —
    scoped by user_id). Once an attachment id is referenced by a
    persisted message, deleting it here would silently break history
    replay for that message, so this is meant to back the UI's "x" on a
    pending upload chip, not for after-the-fact cleanup."""
    att = await attachment_service.get_attachment(session, attachment_id, ctx.user_id)
    if att is None or att.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="attachment not found")
    await attachment_service.delete_attachment(session, attachment_id, ctx.user_id)
