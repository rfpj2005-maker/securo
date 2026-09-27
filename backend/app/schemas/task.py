import uuid
from datetime import date as _Date, datetime, time as _Time
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.subtask import SubtaskRead

_STATUSES = ("pending", "completed")
_RECURRENCE_FREQUENCIES = ("daily", "weekly", "monthly", "yearly")


class TaskCreate(BaseModel):
    title: str = Field(..., max_length=255)
    category: str = Field("administrative", max_length=20)
    due_date: Optional[_Date] = None
    due_time: Optional[_Time] = None
    status: str = "pending"
    notes: Optional[str] = None
    recurrence_frequency: Optional[str] = None
    recurrence_interval: int = Field(1, ge=1)
    recurrence_end_date: Optional[_Date] = None

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

    @field_validator("recurrence_frequency")
    @classmethod
    def validate_recurrence_frequency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _RECURRENCE_FREQUENCIES:
            raise ValueError(f"recurrence_frequency must be one of {_RECURRENCE_FREQUENCIES}")
        return v

    @model_validator(mode="after")
    def validate_recurrence_needs_due_date(self):
        if self.recurrence_frequency and not self.due_date:
            raise ValueError("recurrence_frequency requires a due_date to repeat from")
        return self


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=20)
    due_date: Optional[_Date] = None
    due_time: Optional[_Time] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    recurrence_frequency: Optional[str] = None
    recurrence_interval: Optional[int] = Field(None, ge=1)
    recurrence_end_date: Optional[_Date] = None

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

    @field_validator("recurrence_frequency")
    @classmethod
    def validate_recurrence_frequency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _RECURRENCE_FREQUENCIES:
            raise ValueError(f"recurrence_frequency must be one of {_RECURRENCE_FREQUENCIES}")
        return v


class TaskRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    category: str
    due_date: Optional[_Date] = None
    due_time: Optional[_Time] = None
    status: str
    notes: Optional[str] = None
    source_meeting_id: Optional[uuid.UUID] = None
    recurrence_frequency: Optional[str] = None
    recurrence_interval: int = 1
    recurrence_end_date: Optional[_Date] = None
    created_at: datetime
    updated_at: datetime
    subtasks: list[SubtaskRead] = []

    model_config = ConfigDict(from_attributes=True)
