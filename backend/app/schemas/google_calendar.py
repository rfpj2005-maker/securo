from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GoogleCalendarStatus(BaseModel):
    connected: bool
    google_email: Optional[str] = None
    selected_calendar_id: Optional[str] = None


class GoogleCalendarInfo(BaseModel):
    id: str
    summary: str
    primary: bool = False


class GoogleCalendarSelect(BaseModel):
    calendar_id: str = Field(..., min_length=1)


class CalendarEventCreate(BaseModel):
    summary: str = Field(..., max_length=500)
    description: Optional[str] = None
    location: Optional[str] = None
    # ISO 8601. When all_day is true these are plain dates (YYYY-MM-DD).
    start: datetime
    end: datetime
    all_day: bool = False


class CalendarEventUpdate(BaseModel):
    summary: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    location: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    all_day: Optional[bool] = None


class CalendarEventRead(BaseModel):
    id: str
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    start: str
    end: str
    all_day: bool
    html_link: Optional[str] = None
    calendar_id: str
    calendar_summary: Optional[str] = None
