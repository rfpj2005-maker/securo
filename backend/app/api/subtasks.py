import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import (
    WorkspaceContext,
    current_writable_workspace,
)
from app.schemas.subtask import SubtaskCreate, SubtaskRead, SubtaskUpdate
from app.services import subtask_service

router = APIRouter(prefix="/api/tasks/{task_id}/subtasks", tags=["subtasks"])


@router.post("", response_model=SubtaskRead, status_code=status.HTTP_201_CREATED)
async def create_subtask(
    task_id: uuid.UUID,
    data: SubtaskCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    subtask = await subtask_service.create_subtask(session, task_id, ctx.workspace.id, data)
    if not subtask:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return subtask


@router.patch("/{subtask_id}", response_model=SubtaskRead)
async def update_subtask(
    task_id: uuid.UUID,
    subtask_id: uuid.UUID,
    data: SubtaskUpdate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    subtask = await subtask_service.update_subtask(session, subtask_id, ctx.workspace.id, data)
    if not subtask or subtask.task_id != task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtask not found")
    return subtask


@router.delete("/{subtask_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subtask(
    task_id: uuid.UUID,
    subtask_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    subtask = await subtask_service.get_subtask(session, subtask_id, ctx.workspace.id)
    if not subtask or subtask.task_id != task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtask not found")
    await subtask_service.delete_subtask(session, subtask_id, ctx.workspace.id)
