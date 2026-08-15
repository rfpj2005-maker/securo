import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subtask import Subtask
from app.models.task import Task
from app.schemas.subtask import SubtaskCreate, SubtaskUpdate


async def _task_in_workspace(session: AsyncSession, task_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
    result = await session.execute(
        select(Task.id).where(Task.id == task_id, Task.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none() is not None


async def create_subtask(
    session: AsyncSession,
    task_id: uuid.UUID,
    workspace_id: uuid.UUID,
    data: SubtaskCreate,
) -> Optional[Subtask]:
    if not await _task_in_workspace(session, task_id, workspace_id):
        return None

    next_position = await session.scalar(
        select(func.coalesce(func.max(Subtask.position), -1) + 1).where(Subtask.task_id == task_id)
    )
    subtask = Subtask(task_id=task_id, workspace_id=workspace_id, title=data.title, position=next_position)
    session.add(subtask)
    await session.commit()
    await session.refresh(subtask)
    return subtask


async def get_subtask(session: AsyncSession, subtask_id: uuid.UUID, workspace_id: uuid.UUID) -> Optional[Subtask]:
    result = await session.execute(
        select(Subtask).where(Subtask.id == subtask_id, Subtask.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()


async def update_subtask(
    session: AsyncSession, subtask_id: uuid.UUID, workspace_id: uuid.UUID, data: SubtaskUpdate
) -> Optional[Subtask]:
    subtask = await get_subtask(session, subtask_id, workspace_id)
    if not subtask:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(subtask, key, value)

    await session.commit()
    await session.refresh(subtask)
    return subtask


async def delete_subtask(session: AsyncSession, subtask_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
    subtask = await get_subtask(session, subtask_id, workspace_id)
    if not subtask:
        return False

    await session.delete(subtask)
    await session.commit()
    return True
