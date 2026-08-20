from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.user import User
from app.schemas.gmail import (
    GmailDraftCreate,
    GmailDraftResult,
    GmailMessageRead,
    GmailMessageSummary,
    GmailSendResult,
    GmailStatus,
)
from app.services import gmail_service as gmail

router = APIRouter(prefix="/api/integrations/gmail", tags=["gmail"])


async def _require_connection(session: AsyncSession, user: User):
    conn = await gmail.get_connection(session, user.id)
    if conn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gmail not connected")
    return conn


@router.get("/status", response_model=GmailStatus)
async def status_(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await gmail.get_connection(session, user.id)
    if conn is None:
        return GmailStatus(connected=False)
    return GmailStatus(connected=True, gmail_email=conn.gmail_email)


@router.get("/connect")
async def connect(user: User = Depends(current_active_user)):
    try:
        url = gmail.build_authorize_url(user.id)
    except gmail.GmailNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"authorize_url": url}


@router.get("/callback")
async def callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    frontend_url = get_settings().frontend_url.rstrip("/")
    if error or not code or not state:
        return RedirectResponse(f"{frontend_url}/agents/connections?gmail_error=1")
    try:
        user_id = gmail.verify_state(state)
        await gmail.exchange_code(session, user_id, code)
    except Exception:
        return RedirectResponse(f"{frontend_url}/agents/connections?gmail_error=1")
    return RedirectResponse(f"{frontend_url}/agents/connections?gmail_connected=1")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    await gmail.disconnect(session, user.id)


@router.get("/messages", response_model=list[GmailMessageSummary])
async def search_messages(
    q: str = Query(..., min_length=1),
    max_results: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    try:
        return await gmail.search_messages(session, conn, query=q, max_results=max_results)
    except gmail.GmailNotConnected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/messages/{message_id}", response_model=GmailMessageRead)
async def get_message(
    message_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    try:
        return await gmail.get_message(session, conn, message_id)
    except gmail.GmailNotConnected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/drafts", response_model=GmailDraftResult, status_code=status.HTTP_201_CREATED)
async def create_draft(
    data: GmailDraftCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    try:
        return await gmail.create_draft(
            session, conn, to=data.to, subject=data.subject, body=data.body, cc=data.cc, bcc=data.bcc
        )
    except gmail.GmailNotConnected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/send", response_model=GmailSendResult)
async def send_message(
    data: GmailDraftCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    conn = await _require_connection(session, user)
    try:
        return await gmail.send_message(
            session, conn, to=data.to, subject=data.subject, body=data.body, cc=data.cc, bcc=data.bcc
        )
    except gmail.GmailNotConnected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
