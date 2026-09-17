"""Shared helpers for serializing model rows into LLM-friendly dicts.

Keep payloads small and stable: a transaction returned to the LLM should
have a small set of obviously-named fields, not the full SQLAlchemy row.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Optional


def parse_date(v: Any) -> Optional[date]:
    if v is None or v == "":
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    return date.fromisoformat(str(v))


def parse_time(v: Any) -> Optional[time]:
    if v is None or v == "":
        return None
    if isinstance(v, time):
        return v
    return time.fromisoformat(str(v))


def parse_uuid(v: Any) -> Optional[uuid.UUID]:
    if v is None or v == "":
        return None
    if isinstance(v, uuid.UUID):
        return v
    return uuid.UUID(str(v))


def parse_uuid_list(v: Any) -> Optional[list[uuid.UUID]]:
    if v is None:
        return None
    values = v if isinstance(v, (list, tuple)) else [v]
    return [
        u
        for x in values
        if (u := parse_uuid(x)) is not None
    ] or None


def num(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, Decimal):
        return float(x)
    return float(x)


async def resolve_workspace_id(session, ctx) -> uuid.UUID:
    """Return the workspace the call operates in.

    Prefer the explicit `ws_id` claim from the JWT. Fall back to the
    caller's default (first) workspace — supports tokens minted before
    the workspace migration AND keeps single-workspace callers free of
    having to specify a workspace.
    """
    if ctx.workspace_id is not None:
        return ctx.workspace_id
    from app.models.user import User
    from app.services.workspace_service import get_default_workspace

    user = await session.get(User, ctx.user_id)
    if user is None:
        raise ValueError("No workspace available for this user")
    ws = await get_default_workspace(session, user)
    if ws is None:
        raise ValueError("No workspace available for this user")
    return ws.id


async def resolve_workspace_id_gated(session, ctx, module_id: str) -> uuid.UUID:
    """Same as `resolve_workspace_id`, plus enforces `module_id` the same
    way `require_module` does at the HTTP layer (app/core/workspace_context.py).

    Every tool that reads or writes module-gated data (transactions,
    accounts, categories, budgets, ...) resolves its workspace through
    here instead of the plain `resolve_workspace_id` — MCP tools call the
    service layer directly and never go through FastAPI dependency
    injection, so nothing else on this path enforces
    WorkspaceMemberHiddenModule. Added 2026-09-17 alongside the HTTP fix,
    after confirming a member with a module hidden could still get that
    data by asking the chat agent instead of hitting the API directly.

    Raises ValueError (surfaced to the LLM as a failed tool call, so it
    can't quietly work around a refusal) when the calling member has
    `module_id` hidden. Owners/managers are never restricted, same as
    everywhere else this is enforced.
    """
    from app.models.workspace import WorkspaceMember
    from app.services.workspace_service import get_hidden_module_ids, is_workspace_manager
    from sqlalchemy import select

    ws_id = await resolve_workspace_id(session, ctx)

    if await is_workspace_manager(session, ws_id, ctx.user_id):
        return ws_id

    member = (
        await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws_id,
                WorkspaceMember.user_id == ctx.user_id,
            )
        )
    ).scalar_one_or_none()
    if member is None:
        raise ValueError("Not a member of this workspace")
    if member.role in ("owner", "manager"):
        return ws_id

    hidden = await get_hidden_module_ids(session, member.id)
    if module_id in hidden:
        raise ValueError(
            f"You don't have access to the '{module_id}' module in this workspace."
        )
    return ws_id
