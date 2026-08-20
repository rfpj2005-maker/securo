from typing import Optional

from pydantic import BaseModel


class GmailStatus(BaseModel):
    connected: bool
    gmail_email: Optional[str] = None


class GmailMessageSummary(BaseModel):
    id: str
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    to: Optional[str] = None
    date: Optional[str] = None
    snippet: Optional[str] = None
    labels: list[str] = []


class GmailMessageRead(GmailMessageSummary):
    body: str = ""


class GmailDraftCreate(BaseModel):
    to: str
    subject: str = ""
    body: str = ""
    cc: Optional[str] = None
    bcc: Optional[str] = None


class GmailDraftResult(BaseModel):
    id: str
    message_id: Optional[str] = None


class GmailSendResult(BaseModel):
    sent: bool = True
    message_id: Optional[str] = None
