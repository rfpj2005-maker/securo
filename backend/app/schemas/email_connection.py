from typing import Optional

from pydantic import BaseModel, Field


class EmailConnectionCreate(BaseModel):
    email_address: str = Field(..., min_length=3)
    imap_host: str = Field(..., min_length=1)
    imap_port: int = Field(993, ge=1, le=65535)
    imap_use_ssl: bool = True
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class EmailConnectionStatus(BaseModel):
    connected: bool
    email_address: Optional[str] = None
    imap_host: Optional[str] = None


class EmailMessageSummary(BaseModel):
    id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    date: Optional[str] = None
    snippet: Optional[str] = None
    unread: bool = False


class EmailMessageRead(EmailMessageSummary):
    body: str = ""


class EmailDraftCreate(BaseModel):
    to: str
    subject: str = ""
    body: str = ""
    cc: Optional[str] = None
    bcc: Optional[str] = None


class EmailDraftResult(BaseModel):
    folder: str


class EmailSendResult(BaseModel):
    sent: bool = True
