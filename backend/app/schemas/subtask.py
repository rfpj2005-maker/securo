import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SubtaskCreate(BaseModel):
    title: str = Field(..., max_length=255)


class SubtaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    is_done: Optional[bool] = None
    position: Optional[int] = None


class SubtaskRead(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    title: str
    is_done: bool
    position: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
