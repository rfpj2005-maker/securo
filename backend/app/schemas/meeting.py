import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.task import TaskRead

MEETING_TYPES = ("in_person", "online")


class MeetingListItem(BaseModel):
    id: uuid.UUID
    title: str
    meeting_type: str
    status: str
    error: Optional[str] = None
    duration_seconds: Optional[int] = None
    summary: Optional[str] = None
    recorded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingRead(MeetingListItem):
    transcript: Optional[str] = None
    created_tasks: list[TaskRead] = []
