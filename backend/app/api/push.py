from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.user import User
from app.schemas.push import PushStatus, PushSubscribeCreate, PushUnsubscribe, PushVapidKey
from app.services import push_service

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/vapid-public-key", response_model=PushVapidKey)
async def vapid_public_key():
    settings = get_settings()
    if not settings.vapid_public_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Push notifications are not configured")
    return PushVapidKey(public_key=settings.vapid_public_key)


@router.get("/status", response_model=PushStatus)
async def push_status(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    subs = await push_service.list_subscriptions(session, user.id)
    return PushStatus(subscribed=len(subs) > 0, device_count=len(subs))


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe(
    data: PushSubscribeCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    await push_service.save_subscription(
        session,
        user.id,
        endpoint=data.endpoint,
        p256dh=data.keys.p256dh,
        auth=data.keys.auth,
        user_agent=data.user_agent,
    )
    return {"ok": True}


@router.post("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    data: PushUnsubscribe,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    await push_service.remove_subscription(session, user.id, data.endpoint)


@router.post("/test")
async def send_test(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    try:
        sent = await push_service.notify_user(
            session, user.id, title="Securo", body="Notificações estão funcionando neste aparelho."
        )
    except push_service.PushNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if sent == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active subscription for this device")
    return {"sent": sent}
