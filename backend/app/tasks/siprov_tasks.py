"""Periodic local cache of the Siprov associado portfolio, refreshed
straight from the live Siprov API. Backs the siprov_carteira_cache MCP
tool (see mcp_server/tools/siprov.py) — a fast, full-portfolio read for
bulk/aggregate questions, and a fallback when the live API itself is
down (that has genuinely happened for hours, see 2026-09-02/03).

This used to be sourced from a CSV mirrored out of the workspace admin's
personal Obsidian vault. That vault moved off this server entirely on
2026-09-03/04 (to a local+Obsidian-Sync setup on his own machine,
specifically to keep personal data out of the shared Amparar server),
which orphaned that approach — this task replaces it with a source the
server can own outright: the same API every other siprov_* tool already
calls, cached locally instead of re-fetched from Obsidian.

Reuses mcp_server.tools.siprov's own auth/fetch helpers (_siprov_get)
rather than duplicating Siprov API/credential logic in a second place.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from app.worker import celery_app

logger = logging.getLogger(__name__)

_CACHE_DIR = "/app/data/siprov_cache"
_CACHE_PATH = f"{_CACHE_DIR}/carteira.json"
# Generous ceiling: the real portfolio is ~1,300-2,000 associados at up to
# 1000 itens/page, so this comfortably covers years of growth.
_MAX_PAGES = 50


async def _fetch_all_associados() -> list[dict]:
    from mcp_server.tools.siprov import _siprov_get

    all_items: list[dict] = []
    pagina = 1
    while pagina <= _MAX_PAGES:
        # Siprov's `nome` filter is server-side ignored for this endpoint
        # (confirmed elsewhere in this codebase) — any non-empty value just
        # satisfies a required-param check. `pagina` is what actually walks
        # the full portfolio, in order, until proximaPagina is false.
        page = await _siprov_get("/ext/associado", {"nome": "a", "pagina": pagina})
        itens = page.get("itens") if isinstance(page, dict) else None
        if isinstance(itens, list):
            all_items.extend(itens)
        if not (isinstance(page, dict) and page.get("proximaPagina")):
            break
        pagina += 1
    return all_items


async def _sync_siprov_carteira() -> int:
    items = await _fetch_all_associados()
    os.makedirs(_CACHE_DIR, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quantidade": len(items),
        "itens": items,
    }
    # Write-then-rename so a reader never sees a half-written file, even if
    # this task and an MCP tool call race each other.
    tmp_path = f"{_CACHE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp_path, _CACHE_PATH)
    return len(items)


@celery_app.task(name="app.tasks.siprov_tasks.sync_siprov_carteira")
def sync_siprov_carteira() -> None:
    count = asyncio.run(_sync_siprov_carteira())
    logger.info("Siprov carteira cache refreshed: %d associados", count)
