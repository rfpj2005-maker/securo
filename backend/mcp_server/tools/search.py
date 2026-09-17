from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import search_service
from mcp_server.auth import CallContext
from mcp_server.registry import tool
from mcp_server.tools._helpers import resolve_workspace_id

# Mirrors app/api/search.py's _TYPE_MODULE — a member with a module hidden
# never gets hits of that type from the agent either, same fail-closed
# rule as every other MCP tool in this package (see resolve_workspace_id_gated).
_TYPE_MODULE = {
    "transaction": "transactions",
    "account": "accounts",
    "payee": "payees",
    "category": "categories",
    "goal": "goals",
    "asset": "assets",
}


@tool(
    name="search_all",
    description=(
        "Global text search across the user's entities (transactions, "
        "accounts, categories, payees, etc.). Returns up to N hits per type."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "per_type_limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 5},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    tags=["read", "search"],
)
async def search_all(
    *,
    session: AsyncSession,
    ctx: CallContext,
    query: str,
    per_type_limit: int = 5,
) -> dict[str, Any]:
    ws_id = await resolve_workspace_id(session, ctx)

    from app.models.workspace import WorkspaceMember
    from app.services.workspace_service import get_hidden_module_ids, is_workspace_manager
    from sqlalchemy import select

    allowed_types = None
    if not await is_workspace_manager(session, ws_id, ctx.user_id):
        member = (
            await session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == ws_id,
                    WorkspaceMember.user_id == ctx.user_id,
                )
            )
        ).scalar_one_or_none()
        if member is not None and member.role not in ("owner", "manager"):
            hidden = await get_hidden_module_ids(session, member.id)
            allowed_types = {t for t, module_id in _TYPE_MODULE.items() if module_id not in hidden}

    hits = await search_service.search_all(
        session, ws_id, ctx.user_id, query, per_type_limit=int(per_type_limit), allowed_types=allowed_types
    )
    return {"items": hits, "total": len(hits)}
