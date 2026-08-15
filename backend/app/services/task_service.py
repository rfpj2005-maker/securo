import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


async def get_tasks(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> list[Task]:
    stmt = select(Task).where(Task.workspace_id == workspace_id).options(selectinload(Task.subtasks))
    if category:
        stmt = stmt.where(Task.category == category)
    if status:
        stmt = stmt.where(Task.status == status)
    stmt = stmt.order_by(Task.due_date.is_(None), Task.due_date, Task.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_task(session: AsyncSession, task_id: uuid.UUID, workspace_id: uuid.UUID) -> Optional[Task]:
    result = await session.execute(
        select(Task)
        .where(Task.id == task_id, Task.workspace_id == workspace_id)
        .options(selectinload(Task.subtasks))
    )
    return result.scalar_one_or_none()


async def create_task(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    data: TaskCreate,
) -> Task:
    task = Task(user_id=user_id, workspace_id=workspace_id, **data.model_dump())
    session.add(task)
    await session.commit()
    await session.refresh(task)
    await session.refresh(task, attribute_names=["subtasks"])
    return task


async def update_task(
    session: AsyncSession, task_id: uuid.UUID, workspace_id: uuid.UUID, data: TaskUpdate
) -> Optional[Task]:
    task = await get_task(session, task_id, workspace_id)
    if not task:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    await session.commit()
    await session.refresh(task)
    await session.refresh(task, attribute_names=["subtasks"])
    return task


async def delete_task(session: AsyncSession, task_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
    task = await get_task(session, task_id, workspace_id)
    if not task:
        return False

    await session.delete(task)
    await session.commit()
    return True
