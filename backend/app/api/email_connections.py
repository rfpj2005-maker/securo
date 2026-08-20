from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.database import get_async_session
from app.models.user import User
from app.schemas.email_connection import (
    EmailConnectionCreate,
    EmailConnectionStatus,
    EmailDraftCreate,
    EmailDraftResult,
    EmailMessageRead,
    EmailMessageSummary,
    EmailSendResult,
)
from app.services import email_imap_service as email_svc

router = APIRouter(prefix="/api/integrations/email", tags=["email"])


async def _require_connection(session: AsyncSession, user: User):
    conn = await email_svc.get_connection(session, user.id)
    if conn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email account not connected")
    return conn


@router.get("/status", response_model=EmailConnectionStatus)
async def status_(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await email_svc.get_connection(session, user.id)
    if conn is None:
        return EmailConnectionStatus(connected=False)
    return EmailConnectionStatus(connected=True, email_address=conn.email_address, imap_host=conn.imap_host)


@router.post("", response_model=EmailConnectionStatus, status_code=status.HTTP_201_CREATED)
async def connect(
    data: EmailConnectionCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    try:
        conn = await email_svc.create_or_update(session, user.id, data)
    except email_svc.EmailConnectionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return EmailConnectionStatus(connected=True, email_address=conn.email_address, imap_host=conn.imap_host)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    await email_svc.disconnect(session, user.id)


@router.get("/messages", response_model=list[EmailMessageSummary])
async def search_messages(
    criteria: str = Query("UNSEEN", description="IMAP SEARCH criteria, e.g. UNSEEN, ALL, FROM \"x\", SUBJECT \"x\""),
    max_results: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    try:
        return await email_svc.search_messages(session, conn, criteria=criteria, max_results=max_results)
    except (email_svc.EmailNotConnected, email_svc.EmailConnectionError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/messages/{message_id}", response_model=EmailMessageRead)
async def get_message(
    message_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    try:
        return await email_svc.get_message(session, conn, message_id)
    except (email_svc.EmailNotConnected, email_svc.EmailConnectionError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/drafts", response_model=EmailDraftResult, status_code=status.HTTP_201_CREATED)
async def create_draft(
    data: EmailDraftCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    try:
        return await email_svc.create_draft(
            session, conn, to=data.to, subject=data.subject, body=data.body, cc=data.cc, bcc=data.bcc
        )
    except (email_svc.EmailNotConnected, email_svc.EmailConnectionError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/send", response_model=EmailSendResult)
async def send_message(
    data: EmailDraftCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    try:
        return await email_svc.send_message(
            session, conn, to=data.to, subject=data.subject, body=data.body, cc=data.cc, bcc=data.bcc
        )
    except (email_svc.EmailNotConnected, email_svc.EmailConnectionError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
