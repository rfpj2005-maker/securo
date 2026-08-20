from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import gmail_service as gmail
from mcp_server.auth import CallContext
from mcp_server.registry import tool


async def _require_connection(session: AsyncSession, ctx: CallContext):
    conn = await gmail.get_connection(session, ctx.user_id)
    if conn is None:
        raise ValueError("Gmail is not connected. Ask the user to connect it on the Connections page first.")
    return conn


# Mirrors mcp_server.tools.proposals._PROPOSAL_PREFACE/_APPLY_FIELD, adapted
# for "saved as draft" instead of "written to the DB" — duplicated locally
# rather than imported since the two modules aren't otherwise coupled.
_DRAFT_PROPOSAL_PREFACE = (
    "[PROPOSAL — PREVIEW ONLY, NOT SENT. This only ever creates a DRAFT; it "
    "never sends anything. The user MUST confirm before the draft is saved. "
    "In Securo's UI an Apply button renders automatically — do not "
    "duplicate the details in your reply. When running through an external "
    "MCP client (no Apply button in chat), pass apply=true on a follow-up "
    "call AFTER the user explicitly confirms in the conversation. Never set "
    "apply=true on the first call. Describe results as 'I prepared a "
    "draft…' / 'Preparei um rascunho…' — NEVER as 'I sent' / 'Enviei' / "
    "'Done' unless the response includes applied=true.] "
)

_APPLY_FIELD = {
    "type": "boolean",
    "default": False,
    "description": (
        "External clients only. When true (and the call is authenticated "
        "with an external MCP token), saves the draft instead of returning "
        "a preview. Ignored by Securo's internal runtime."
    ),
}

_SEND_PROPOSAL_PREFACE = (
    "[PROPOSAL — PREVIEW ONLY, NOT SENT YET. This IS a real send action — "
    "once applied, the email leaves the user's account and CANNOT be "
    "recalled. The user MUST explicitly confirm before it goes out. In "
    "Securo's UI an Apply button renders automatically — do not duplicate "
    "the details in your reply. When running through an external MCP "
    "client (no Apply button in chat), pass apply=true on a follow-up call "
    "AFTER the user explicitly confirms in the conversation — never on the "
    "first call, and never if there is any ambiguity about recipient or "
    "content. Describe results as 'I prepared a message to send…' / "
    "'Preparei uma mensagem para enviar…' — NEVER as 'I sent' / 'Enviei' / "
    "'Done' unless the response includes applied=true.] "
)

_SEND_APPLY_FIELD = {
    "type": "boolean",
    "default": False,
    "description": (
        "External clients only. When true (and the call is authenticated "
        "with an external MCP token), actually sends the email instead of "
        "returning a preview. Ignored by Securo's internal runtime."
    ),
}


@tool(
    name="search_gmail",
    description=(
        "Search the user's Gmail inbox. `query` uses Gmail's own search syntax — the same thing "
        "you'd type in the Gmail search box (e.g. 'from:cliente@exemplo.com', 'subject:fatura', "
        "'is:unread', 'newer_than:7d'). Returns metadata + snippet only, not the full body — "
        "call get_gmail_message with the id to read the whole thing."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Gmail search syntax"},
            "max_results": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    tags=["read", "gmail"],
)
async def search_gmail(
    *, session: AsyncSession, ctx: CallContext, query: str, max_results: int = 20
) -> dict[str, Any]:
    conn = await _require_connection(session, ctx)
    messages = await gmail.search_messages(session, conn, query=query, max_results=max_results)
    return {"items": messages, "total": len(messages)}


@tool(
    name="get_gmail_message",
    description="Read the full content (headers + body) of one Gmail message. id comes from search_gmail.",
    parameters={
        "type": "object",
        "properties": {
            "message_id": {"type": "string"},
        },
        "required": ["message_id"],
        "additionalProperties": False,
    },
    tags=["read", "gmail"],
)
async def get_gmail_message(*, session: AsyncSession, ctx: CallContext, message_id: str) -> dict[str, Any]:
    conn = await _require_connection(session, ctx)
    return await gmail.get_message(session, conn, message_id)


@tool(
    name="propose_create_gmail_draft",
    description=_DRAFT_PROPOSAL_PREFACE
    + (
        "Build a preview for a new Gmail draft — saved to the user's Drafts folder for them to "
        "review, edit, and send themselves. Never sends anything."
    ),
    parameters={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string"},
            "body": {"type": "string", "description": "Plain-text body"},
            "cc": {"type": "string"},
            "bcc": {"type": "string"},
            "apply": _APPLY_FIELD,
        },
        "required": ["to", "subject", "body"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "gmail"],
)
async def propose_create_gmail_draft(
    *,
    session: AsyncSession,
    ctx: CallContext,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    conn = await _require_connection(session, ctx)
    preview = {
        "kind": "create_email_draft",
        "proposed": {
            "provider": "gmail",
            "mailbox": conn.gmail_email,
            "to": to,
            "subject": subject,
            "body": body,
            "cc": cc,
            "bcc": bcc,
        },
        "apply_endpoint": "POST /api/integrations/gmail/drafts",
    }
    if bool(apply) and ctx.external:
        result = await gmail.create_draft(session, conn, to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        return {**preview, "applied": True, **result}
    return preview


@tool(
    name="propose_send_gmail",
    description=_SEND_PROPOSAL_PREFACE
    + (
        "Build a preview for actually sending an email from the user's Gmail. This is NOT the "
        "same as propose_create_gmail_draft — that one only saves a draft, this one sends for "
        "real once applied. Prefer the draft tool unless the user has clearly asked you to send "
        "it now, not just prepare it."
    ),
    parameters={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string"},
            "body": {"type": "string", "description": "Plain-text body"},
            "cc": {"type": "string"},
            "bcc": {"type": "string"},
            "apply": _SEND_APPLY_FIELD,
        },
        "required": ["to", "subject", "body"],
        "additionalProperties": False,
    },
    is_proposal=True,
    tags=["propose", "gmail"],
)
async def propose_send_gmail(
    *,
    session: AsyncSession,
    ctx: CallContext,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    conn = await _require_connection(session, ctx)
    preview = {
        "kind": "send_email",
        "proposed": {
            "provider": "gmail",
            "mailbox": conn.gmail_email,
            "to": to,
            "subject": subject,
            "body": body,
            "cc": cc,
            "bcc": bcc,
        },
        "apply_endpoint": "POST /api/integrations/gmail/send",
    }
    if bool(apply) and ctx.external:
        result = await gmail.send_message(session, conn, to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        return {**preview, "applied": True, **result}
    return preview
