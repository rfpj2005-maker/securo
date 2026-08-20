"""Web Push (VAPID) — task due-date reminders. Sends directly to the
browser's push service (Chrome → FCM, etc); no third-party push provider
account needed, just the VAPID key pair in Settings.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


class PushNotConfigured(RuntimeError):
    pass


async def save_subscription(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: Optional[str] = None,
) -> PushSubscription:
    existing = (
        await session.execute(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
    ).scalar_one_or_none()
    if existing is not None:
        # Same device re-subscribing (browsers rotate keys occasionally) —
        # keep it attached to whichever user enabled it most recently.
        existing.user_id = user_id
        existing.p256dh = p256dh
        existing.auth = auth
        existing.user_agent = user_agent
        await session.commit()
        await session.refresh(existing)
        return existing

    sub = PushSubscription(user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth, user_agent=user_agent)
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


async def remove_subscription(session: AsyncSession, user_id: uuid.UUID, endpoint: str) -> bool:
    sub = (
        await session.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == endpoint, PushSubscription.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if sub is None:
        return False
    await session.delete(sub)
    await session.commit()
    return True


async def list_subscriptions(session: AsyncSession, user_id: uuid.UUID) -> list[PushSubscription]:
    return list(
        (await session.execute(select(PushSubscription).where(PushSubscription.user_id == user_id)))
        .scalars()
        .all()
    )


def _send_one_sync(sub: PushSubscription, payload: dict[str, Any]) -> bool:
    """Returns True on success, False if the subscription is dead (gone/
    expired — caller should delete it) and re-raises for anything else."""
    settings = get_settings()
    private_key = settings.vapid_private_key.get_secret_value()
    if not private_key or not settings.vapid_claim_email:
        raise PushNotConfigured("VAPID_PRIVATE_KEY / VAPID_CLAIM_EMAIL are not configured.")
    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=private_key,
            vapid_claims={"sub": f"mailto:{settings.vapid_claim_email}"},
        )
        return True
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (404, 410):
            # Subscription no longer exists at the push service (browser
            # data cleared, uninstalled, etc) — dead, not a transient error.
            return False
        logger.warning("Web Push failed for subscription %s: %s", sub.id, exc)
        raise


async def notify_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    title: str,
    body: str,
    url: Optional[str] = None,
) -> int:
    """Sends to every device the user has enabled — cleans up any that the
    push service reports as gone. Returns how many actually received it."""
    import asyncio

    subs = await list_subscriptions(session, user_id)
    if not subs:
        return 0

    payload = {"title": title, "body": body, "url": url or "/tasks"}
    sent = 0
    for sub in subs:
        try:
            ok = await asyncio.to_thread(_send_one_sync, sub, payload)
        except PushNotConfigured:
            raise
        except Exception:
            logger.exception("Unexpected error sending push to subscription %s", sub.id)
            continue
        if ok:
            sent += 1
        else:
            await session.delete(sub)
    if sent < len(subs):
        await session.commit()
    return sent
