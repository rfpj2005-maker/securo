import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import (
    WorkspaceContext,
    current_workspace,
    current_writable_workspace,
)
from app.schemas.meeting import MeetingListItem, MeetingRead
from app.services import meeting_service

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.get("", response_model=list[MeetingListItem])
async def list_meetings(
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return await meeting_service.list_meetings(session, ctx.workspace.id)


@router.get("/{meeting_id}", response_model=MeetingRead)
async def get_meeting(
    meeting_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    meeting = await meeting_service.get_meeting(session, meeting_id, ctx.workspace.id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    created_tasks = await meeting_service.get_meeting_tasks(session, meeting_id, ctx.workspace.id)
    return {
        **MeetingListItem.model_validate(meeting).model_dump(),
        "transcript": meeting.transcript,
        "created_tasks": created_tasks,
    }


@router.post("", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
async def upload_meeting(
    title: str = Form(...),
    meeting_type: str = Form(...),
    file: UploadFile = File(...),
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    payload = await file.read()
    try:
        meeting = await meeting_service.create_meeting_with_audio(
            session,
            workspace_id=ctx.workspace.id,
            user_id=ctx.user_id,
            title=title,
            meeting_type=meeting_type,
            filename=file.filename or "recording.webm",
            payload=payload,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Fire-and-forget Celery dispatch — the task does transcription + summary.
    try:
        from app.worker import celery_app
        celery_app.send_task("app.tasks.meeting_tasks.process_meeting", args=[str(meeting.id)])
    except Exception:  # noqa: BLE001 — dispatch failure shouldn't kill the upload
        await meeting_service.mark_status(session, meeting.id, status="failed", error="Celery dispatch failed")

    return meeting


@router.post("/{meeting_id}/retry", response_model=MeetingRead)
async def retry_meeting(
    meeting_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    meeting = await meeting_service.retry_meeting(session, meeting_id, ctx.workspace.id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    try:
        from app.worker import celery_app
        celery_app.send_task("app.tasks.meeting_tasks.process_meeting", args=[str(meeting.id)])
    except Exception:  # noqa: BLE001
        await meeting_service.mark_status(session, meeting.id, status="failed", error="Celery dispatch failed")

    return meeting


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    deleted = await meeting_service.delete_meeting(session, meeting_id, ctx.workspace.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
