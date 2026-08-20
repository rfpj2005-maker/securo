"""Generic IMAP email integration — for mailboxes that aren't Gmail
(Hostinger, or any other host/port/username/password provider). No OAuth:
credentials are entered once, encrypted at rest, same scheme as every
other stored secret in this codebase (agent_llm_connections, Siprov).

`imaplib`/`email`/`smtplib` are stdlib and synchronous — every call here
runs the blocking I/O in a thread via asyncio.to_thread so it doesn't
stall the event loop, matching how the rest of the agents' I/O stays
async. IMAP handles read + draft (Phases 2-3); SMTP handles actually
sending (Phase 4) — a separate protocol/port on most hosts.
"""
from __future__ import annotations

import asyncio
import email as email_lib
import imaplib
import logging
import re
import smtplib
import time
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.services.crypto import decrypt, encrypt
from app.models.email_connection import EmailConnection
from app.schemas.email_connection import EmailConnectionCreate

logger = logging.getLogger(__name__)


class EmailConnectionError(RuntimeError):
    pass


class EmailNotConnected(RuntimeError):
    pass


async def get_connection(session: AsyncSession, user_id) -> Optional[EmailConnection]:
    return (
        await session.execute(select(EmailConnection).where(EmailConnection.user_id == user_id))
    ).scalar_one_or_none()


def _connect_sync(host: str, port: int, use_ssl: bool, username: str, password: str) -> imaplib.IMAP4:
    client: imaplib.IMAP4 = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
    client.login(username, password)
    return client


async def test_login(data: EmailConnectionCreate) -> None:
    """Raises EmailConnectionError with a human-readable reason on failure."""
    def _try() -> None:
        try:
            client = _connect_sync(data.imap_host, data.imap_port, data.imap_use_ssl, data.username, data.password)
        except (imaplib.IMAP4.error, OSError, TimeoutError) as exc:
            raise EmailConnectionError(str(exc)) from exc
        try:
            client.select("INBOX", readonly=True)
        finally:
            try:
                client.logout()
            except Exception:
                pass

    await asyncio.to_thread(_try)


async def create_or_update(session: AsyncSession, user_id, data: EmailConnectionCreate) -> EmailConnection:
    await test_login(data)  # fail before writing anything if the credentials don't work

    conn = await get_connection(session, user_id)
    if conn is None:
        conn = EmailConnection(user_id=user_id)
        session.add(conn)

    conn.email_address = data.email_address
    conn.imap_host = data.imap_host
    conn.imap_port = data.imap_port
    conn.imap_use_ssl = data.imap_use_ssl
    conn.username = data.username
    conn.password_encrypted = encrypt(data.password)

    await session.commit()
    await session.refresh(conn)
    return conn


async def disconnect(session: AsyncSession, user_id) -> bool:
    conn = await get_connection(session, user_id)
    if conn is None:
        return False
    await session.delete(conn)
    await session.commit()
    return True


def _decode(value: Optional[str]) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _fetch_summary(client: imaplib.IMAP4, uid: bytes) -> Optional[dict[str, Any]]:
    typ, msg_data = client.fetch(uid, "(FLAGS BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
    if typ != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
        return None
    flags_raw = msg_data[0][0].decode("utf-8", errors="replace")
    header_bytes = msg_data[0][1]
    msg = email_lib.message_from_bytes(header_bytes)
    date_str = msg.get("Date")
    try:
        date_iso = parsedate_to_datetime(date_str).isoformat() if date_str else None
    except (TypeError, ValueError):
        date_iso = date_str
    return {
        "id": uid.decode("ascii"),
        "subject": _decode(msg.get("Subject")),
        "sender": _decode(msg.get("From")),
        "date": date_iso,
        "snippet": None,
        "unread": "\\Seen" not in flags_raw,
    }


def _search_sync(conn: EmailConnection, password: str, criteria: str, max_results: int) -> list[dict[str, Any]]:
    client = _connect_sync(conn.imap_host, conn.imap_port, conn.imap_use_ssl, conn.username, password)
    try:
        client.select("INBOX", readonly=True)
        typ, data = client.search(None, criteria)
        if typ != "OK":
            raise EmailConnectionError(f"IMAP SEARCH failed: {typ}")
        uids = data[0].split()
        uids = uids[-max_results:]  # most recent N (IMAP UIDs are assigned in ascending order)
        uids.reverse()
        results = []
        for uid in uids:
            summary = _fetch_summary(client, uid)
            if summary:
                results.append(summary)
        return results
    finally:
        try:
            client.logout()
        except Exception:
            pass


async def search_messages(
    session: AsyncSession, conn: EmailConnection, *, criteria: str = "ALL", max_results: int = 20
) -> list[dict[str, Any]]:
    password = decrypt(conn.password_encrypted)
    if not password:
        raise EmailNotConnected("No password on file — reconnect the email account")
    try:
        return await asyncio.to_thread(_search_sync, conn, password, criteria, max_results)
    except imaplib.IMAP4.error as exc:
        raise EmailConnectionError(str(exc)) from exc


def _extract_body(msg: email_lib.message.Message) -> str:
    if msg.is_multipart():
        plain, html = None, None
        for part in msg.walk():
            ctype = part.get_content_type()
            if part.get_content_disposition() == "attachment":
                continue
            if ctype == "text/plain" and plain is None:
                plain = part.get_payload(decode=True)
            elif ctype == "text/html" and html is None:
                html = part.get_payload(decode=True)
        raw = plain or html
    else:
        raw = msg.get_payload(decode=True)
    if raw is None:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def _get_message_sync(conn: EmailConnection, password: str, message_id: str) -> dict[str, Any]:
    client = _connect_sync(conn.imap_host, conn.imap_port, conn.imap_use_ssl, conn.username, password)
    try:
        client.select("INBOX", readonly=True)
        uid = message_id.encode("ascii")
        typ, msg_data = client.fetch(uid, "(FLAGS RFC822)")
        if typ != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
            raise EmailConnectionError(f"message {message_id} not found")
        flags_raw = msg_data[0][0].decode("utf-8", errors="replace")
        msg = email_lib.message_from_bytes(msg_data[0][1])
        date_str = msg.get("Date")
        try:
            date_iso = parsedate_to_datetime(date_str).isoformat() if date_str else None
        except (TypeError, ValueError):
            date_iso = date_str
        return {
            "id": message_id,
            "subject": _decode(msg.get("Subject")),
            "sender": _decode(msg.get("From")),
            "date": date_iso,
            "snippet": None,
            "unread": "\\Seen" not in flags_raw,
            "body": _extract_body(msg),
        }
    finally:
        try:
            client.logout()
        except Exception:
            pass


async def get_message(session: AsyncSession, conn: EmailConnection, message_id: str) -> dict[str, Any]:
    password = decrypt(conn.password_encrypted)
    if not password:
        raise EmailNotConnected("No password on file — reconnect the email account")
    try:
        return await asyncio.to_thread(_get_message_sync, conn, password, message_id)
    except imaplib.IMAP4.error as exc:
        raise EmailConnectionError(str(exc)) from exc


def _drafts_folder_from_list(client: imaplib.IMAP4) -> Optional[str]:
    """Ask the server which mailbox is flagged \\Drafts rather than
    guessing — server layouts vary (flat "Drafts" vs nested "INBOX.Drafts")."""
    typ, data = client.list()
    if typ != "OK":
        return None
    for raw in data:
        if not raw:
            continue
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        if "\\Drafts" not in line and "\\Draft" not in line:
            continue
        m = re.search(r'"([^"]*)"\s*$', line)
        if m:
            return m.group(1)
        parts = line.rsplit(" ", 1)
        if len(parts) == 2:
            return parts[1].strip('"')
    return None


def _create_draft_sync(
    conn: EmailConnection, password: str, *, to: str, subject: str, body: str, cc: Optional[str], bcc: Optional[str]
) -> dict[str, Any]:
    client = _connect_sync(conn.imap_host, conn.imap_port, conn.imap_use_ssl, conn.username, password)
    try:
        msg = EmailMessage()
        msg["From"] = conn.email_address
        msg["To"] = to
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        msg["Subject"] = subject
        msg.set_content(body)
        msg_bytes = msg.as_bytes()

        detected = _drafts_folder_from_list(client)
        candidates = list(dict.fromkeys(
            ([detected] if detected else []) + ["Drafts", "INBOX.Drafts", "INBOX/Drafts", "Rascunhos", "INBOX.Rascunhos"]
        ))

        last_err = "no candidate folder tried"
        for folder in candidates:
            try:
                typ, resp = client.append(folder, "\\Draft", imaplib.Time2Internaldate(time.time()), msg_bytes)
            except imaplib.IMAP4.error as exc:
                last_err = str(exc)
                continue
            if typ == "OK":
                return {"folder": folder}
            last_err = f"{typ}: {resp}"
        raise EmailConnectionError(f"Could not save the draft to any Drafts folder (tried {candidates}): {last_err}")
    finally:
        try:
            client.logout()
        except Exception:
            pass


async def create_draft(
    session: AsyncSession,
    conn: EmailConnection,
    *,
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> dict[str, Any]:
    """Saves a draft to the mailbox's own Drafts folder via IMAP APPEND —
    never sends anything. The user reviews, edits, and sends it themselves
    from their normal email client."""
    password = decrypt(conn.password_encrypted)
    if not password:
        raise EmailNotConnected("No password on file — reconnect the email account")
    try:
        return await asyncio.to_thread(_create_draft_sync, conn, password, to=to, subject=subject, body=body, cc=cc, bcc=bcc)
    except imaplib.IMAP4.error as exc:
        raise EmailConnectionError(str(exc)) from exc


def _smtp_host(conn: EmailConnection) -> str:
    """Most hosts mirror their IMAP hostname with an "smtp." prefix
    (imap.hostinger.com → smtp.hostinger.com). Used only when the user
    hasn't set an explicit smtp_host override."""
    if conn.smtp_host:
        return conn.smtp_host
    if conn.imap_host[:4].lower() == "imap":
        return "smtp" + conn.imap_host[4:]
    return conn.imap_host


def _send_message_sync(
    conn: EmailConnection, password: str, *, to: str, subject: str, body: str, cc: Optional[str], bcc: Optional[str]
) -> dict[str, Any]:
    msg = EmailMessage()
    msg["From"] = conn.email_address
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    msg["Subject"] = subject
    msg.set_content(body)

    host = _smtp_host(conn)
    port = conn.smtp_port
    try:
        client: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=20) if conn.smtp_use_ssl else smtplib.SMTP(host, port, timeout=20)
    except (OSError, TimeoutError) as exc:
        raise EmailConnectionError(f"Could not reach SMTP server {host}:{port} — {exc}") from exc
    try:
        if not conn.smtp_use_ssl:
            client.starttls()
        client.login(conn.username, password)
        client.send_message(msg)
    finally:
        try:
            client.quit()
        except Exception:
            pass
    return {"sent": True}


async def send_message(
    session: AsyncSession,
    conn: EmailConnection,
    *,
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> dict[str, Any]:
    """Actually sends via SMTP — irreversible, unlike create_draft. Only
    ever called from the apply path (real user click, or an external
    caller that already confirmed with the user)."""
    password = decrypt(conn.password_encrypted)
    if not password:
        raise EmailNotConnected("No password on file — reconnect the email account")
    try:
        return await asyncio.to_thread(_send_message_sync, conn, password, to=to, subject=subject, body=body, cc=cc, bcc=bcc)
    except smtplib.SMTPException as exc:
        raise EmailConnectionError(str(exc)) from exc
