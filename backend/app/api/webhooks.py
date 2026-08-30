"""Webhook receivers for external providers — currently just Pluggy.

Unauthenticated by necessity (the provider calls this directly, there's
no Securo session), so every handler here does the minimum possible with
the payload: look up which of *our* connections it refers to, and kick
off the same resync path the manual "Sincronizar" button and the
scheduled stale-connection sweep already use
(`app.tasks.sync_tasks.sync_single_connection`) — no bespoke per-event
logic, so this can't drift from what a normal sync already does.

Always returns 200 quickly (even on a payload we don't recognize) so the
provider doesn't retry-storm us over something a redeploy will fix
anyway; every inbound call is logged so a shape mismatch is debuggable
after the fact instead of visible only as a silent no-op.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.bank_connection import BankConnection
from app.tasks.sync_tasks import sync_single_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# Events that mean "something changed, go resync" — Pluggy's docs list a
# handful of others (e.g. connector/status-updated) that don't map to a
# specific item, so those are logged and otherwise ignored rather than
# guessed at.
_RESYNC_EVENTS = {
    "item/created",
    "item/updated",
    "transactions/created",
    "transactions/updated",
    "transactions/deleted",
}


def _extract_item_id(payload: dict) -> str | None:
    """Pluggy's webhook payload shape has drifted across their API
    versions in the wild (itemId at the top level vs. nested under
    data.item.id) — check the documented shape first, then the fallback,
    rather than trusting exactly one."""
    if isinstance(payload.get("itemId"), str):
        return payload["itemId"]
    data = payload.get("data")
    if isinstance(data, dict):
        item = data.get("item")
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            return item["id"]
    return None


@router.post("/pluggy")
async def pluggy_webhook(request: Request) -> dict:
    try:
        payload = await request.json()
    except ValueError:
        logger.warning("Pluggy webhook: non-JSON body, ignoring")
        return {"received": True}

    event = payload.get("event")
    item_id = _extract_item_id(payload)
    logger.info("Pluggy webhook received: event=%s itemId=%s", event, item_id)

    if event not in _RESYNC_EVENTS or not item_id:
        return {"received": True}

    async with async_session_maker() as session:
        result = await session.execute(
            select(BankConnection.id, BankConnection.user_id).where(
                BankConnection.provider == "pluggy",
                BankConnection.external_id == item_id,
            )
        )
        row = result.first()

    if row is None:
        logger.info("Pluggy webhook: no connection matches itemId=%s", item_id)
        return {"received": True}

    connection_id, user_id = row
    sync_single_connection.delay(str(connection_id), str(user_id))
    return {"received": True}
