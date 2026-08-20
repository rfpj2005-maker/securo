"""Gmail integration: OAuth2 (authorization-code + refresh) and a thin
wrapper over the Gmail API v1 REST endpoints. Mirrors
google_calendar_service.py's approach (plain httpx, no google-api-python-
client). Phase 1 was read-only (search + read); Phase 2 added drafting
(gmail.compose scope) — sending is still a deliberately separate follow-up.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.services.crypto import decrypt, encrypt
from app.core.config import get_settings
from app.models.gmail_connection import GmailConnection

logger = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
# gmail.compose allows creating/editing/deleting drafts (and sending only
# messages the app itself created) without granting full mailbox write
# access. Sending an already-existing message would need gmail.send —
# deliberately not requested yet.
SCOPES = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose openid email"

STATE_ALGO = "HS256"


class GmailNotConfigured(RuntimeError):
    pass


class GmailNotConnected(RuntimeError):
    pass


def _client_credentials() -> tuple[str, str]:
    settings = get_settings()
    client_id = settings.google_oauth_client_id
    client_secret = settings.google_oauth_client_secret.get_secret_value()
    if not client_id or not client_secret:
        raise GmailNotConfigured("Google OAuth client ID/secret are not configured")
    return client_id, client_secret


def _redirect_uri() -> str:
    return f"{get_settings().frontend_url.rstrip('/')}/api/integrations/gmail/callback"


def build_authorize_url(user_id: uuid.UUID) -> str:
    client_id, _ = _client_credentials()
    state = jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        get_settings().secret_key.get_secret_value(),
        algorithm=STATE_ALGO,
    )
    params = {
        "client_id": client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def verify_state(state: str) -> uuid.UUID:
    try:
        payload = jwt.decode(state, get_settings().secret_key.get_secret_value(), algorithms=[STATE_ALGO])
    except JWTError as exc:
        raise ValueError("invalid or expired state") from exc
    return uuid.UUID(payload["sub"])


async def exchange_code(session: AsyncSession, user_id: uuid.UUID, code: str) -> GmailConnection:
    client_id, client_secret = _client_credentials()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()

        userinfo_resp = await client.get(
            USERINFO_URL, headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        userinfo_resp.raise_for_status()
        email = userinfo_resp.json().get("email")

    conn = await get_connection(session, user_id)
    if conn is None:
        conn = GmailConnection(user_id=user_id)
        session.add(conn)

    conn.gmail_email = email
    conn.access_token_encrypted = encrypt(tokens["access_token"])
    if tokens.get("refresh_token"):
        # Google only returns a refresh_token on first consent (or when
        # prompt=consent forces re-issue, which we always pass) — never
        # overwrite a previously stored one with an absent value.
        conn.refresh_token_encrypted = encrypt(tokens["refresh_token"])
    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))

    await session.commit()
    await session.refresh(conn)
    return conn


async def get_connection(session: AsyncSession, user_id: uuid.UUID) -> Optional[GmailConnection]:
    return (
        await session.execute(select(GmailConnection).where(GmailConnection.user_id == user_id))
    ).scalar_one_or_none()


async def disconnect(session: AsyncSession, user_id: uuid.UUID) -> bool:
    conn = await get_connection(session, user_id)
    if conn is None:
        return False
    await session.delete(conn)
    await session.commit()
    return True


async def _access_token(session: AsyncSession, conn: GmailConnection) -> str:
    """Return a valid access token, refreshing it first if it's expired
    (or about to expire in the next minute)."""
    now = datetime.now(timezone.utc)
    if conn.token_expires_at and conn.token_expires_at > now + timedelta(minutes=1) and conn.access_token_encrypted:
        token = decrypt(conn.access_token_encrypted)
        if token:
            return token

    refresh_token = decrypt(conn.refresh_token_encrypted)
    if not refresh_token:
        raise GmailNotConnected("No refresh token on file — reconnect Gmail")

    client_id, client_secret = _client_credentials()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()

    conn.access_token_encrypted = encrypt(tokens["access_token"])
    conn.token_expires_at = now + timedelta(seconds=tokens.get("expires_in", 3600))
    await session.commit()
    return tokens["access_token"]


async def _gmail_request(
    session: AsyncSession, conn: GmailConnection, method: str, path: str, **kwargs: Any
) -> httpx.Response:
    token = await _access_token(session, conn)
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.request(
            method, f"{GMAIL_API}{path}", headers={"Authorization": f"Bearer {token}"}, **kwargs
        )
        resp.raise_for_status()
        return resp


def _header(headers: list[dict[str, str]], name: str) -> Optional[str]:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def _decode_b64url(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _extract_body(payload: dict[str, Any]) -> str:
    """Walks the MIME part tree for the first text/plain part; falls back
    to text/html (tags left in — good enough for an agent to read) if
    that's all a message has."""
    def walk(part: dict[str, Any]) -> dict[str, str]:
        found: dict[str, str] = {}
        mime = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")
        if body_data and mime in ("text/plain", "text/html") and mime not in found:
            found[mime] = _decode_b64url(body_data)
        for sub in part.get("parts", []) or []:
            for k, v in walk(sub).items():
                found.setdefault(k, v)
        return found

    parts = walk(payload)
    return parts.get("text/plain") or parts.get("text/html") or ""


def _message_summary(msg: dict[str, Any]) -> dict[str, Any]:
    headers = msg.get("payload", {}).get("headers", [])
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "subject": _header(headers, "Subject"),
        "sender": _header(headers, "From"),
        "to": _header(headers, "To"),
        "date": _header(headers, "Date"),
        "snippet": msg.get("snippet"),
        "labels": msg.get("labelIds", []),
    }


async def search_messages(
    session: AsyncSession, conn: GmailConnection, *, query: str, max_results: int = 20
) -> list[dict[str, Any]]:
    """`query` uses Gmail's native search syntax (from:, subject:, is:unread,
    newer_than:7d, etc.) — the same thing you'd type in the Gmail search box."""
    resp = await _gmail_request(
        session, conn, "GET", "/users/me/messages",
        params={"q": query, "maxResults": max_results},
    )
    ids = [m["id"] for m in resp.json().get("messages", [])]
    if not ids:
        return []

    async def _fetch_metadata(msg_id: str) -> dict[str, Any]:
        r = await _gmail_request(
            session, conn, "GET", f"/users/me/messages/{msg_id}",
            params={"format": "metadata", "metadataHeaders": ["Subject", "From", "To", "Date"]},
        )
        return _message_summary(r.json())

    results = await asyncio.gather(*[_fetch_metadata(i) for i in ids], return_exceptions=True)
    messages: list[dict[str, Any]] = []
    for msg_id, result in zip(ids, results):
        if isinstance(result, BaseException):
            logger.warning("failed to fetch gmail message %s: %s", msg_id, result)
            continue
        messages.append(result)
    return messages


async def get_message(session: AsyncSession, conn: GmailConnection, message_id: str) -> dict[str, Any]:
    resp = await _gmail_request(
        session, conn, "GET", f"/users/me/messages/{message_id}", params={"format": "full"}
    )
    data = resp.json()
    summary = _message_summary(data)
    summary["body"] = _extract_body(data.get("payload", {}))
    return summary


async def create_draft(
    session: AsyncSession,
    conn: GmailConnection,
    *,
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> dict[str, Any]:
    """Saves a draft to Gmail's own Drafts folder — never sends anything.
    The user reviews, edits, and sends it themselves from Gmail."""
    msg = EmailMessage()
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    msg["Subject"] = subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")

    resp = await _gmail_request(
        session, conn, "POST", "/users/me/drafts", json={"message": {"raw": raw}}
    )
    data = resp.json()
    return {"id": data["id"], "message_id": data.get("message", {}).get("id")}


async def send_message(
    session: AsyncSession,
    conn: GmailConnection,
    *,
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> dict[str, Any]:
    """Actually sends — irreversible, unlike create_draft. gmail.compose
    covers this (it grants send, scoped to messages the app itself
    composes — not arbitrary mailbox write access). Only ever called from
    the apply path (real user click, or an external caller that already
    confirmed with the user)."""
    msg = EmailMessage()
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    msg["Subject"] = subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")

    resp = await _gmail_request(
        session, conn, "POST", "/users/me/messages/send", json={"raw": raw}
    )
    data = resp.json()
    return {"sent": True, "message_id": data.get("id")}
