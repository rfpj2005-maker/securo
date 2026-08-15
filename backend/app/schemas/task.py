import uuid
from datetime import date as _Date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.subtask import SubtaskRead

_STATUSES = ("pending", "completed")


class TaskCreate(BaseModel):
    title: str = Field(..., max_length=255)
    category: str = Field("administrative", max_length=20)
    due_date: Optional[_Date] = None
    status: str = "pending"

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("category cannot be empty")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _STATUSES:
            raise ValueError(f"status must be one of {_STATUSES}")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=20)
    due_date: Optional[_Date] = None
    status: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("category cannot be empty")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _STATUSES:
            raise ValueError(f"status must be one of {_STATUSES}")
        return v


class TaskRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    category: str
    due_date: Optional[_Date] = None
    status: str
    source_meeting_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    subtasks: list[SubtaskRead] = []

    model_config = ConfigDict(from_attributes=True)
