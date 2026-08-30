"""Pairing flow for headless companion devices — currently just the Wear
OS watch app — that can't reasonably enter an email+password.

Mirrors the 2FA temp-token pattern in `two_factor.py`: a short code
stored in Redis, redeemed once for a normal access token. The web app is
the only place a code can be minted (`/watch-pair/start`, authenticated
— the user is already logged in there); the device redeems it
(`/watch-pair/redeem`, unauthenticated — same family as `/login`, since
the device has no session yet).

Token lifetime is whatever `get_jwt_strategy()` already issues (24h, no
refresh endpoint) — deliberately not a longer-lived "device token" yet.
That's a real UX cost (daily re-pair) but keeps this from introducing a
second token-lifetime/security surface before anyone has actually lived
with the shorter one.
"""
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user, get_jwt_strategy
from app.core.database import get_async_session
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.watch_pairing import (
    WatchPairRedeemRequest,
    WatchPairStartResponse,
    WatchPairTokenResponse,
)

router = APIRouter()

# 10 minutes: long enough to read a 6-digit code off a phone screen and
# thumb it in on a watch, short enough to keep the brute-force window
# (rate-limited separately, see main.py's `login_rate_limit` on this
# router) tight.
CODE_TTL_SECONDS = 600
_CODE_LENGTH = 6


def _generate_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(_CODE_LENGTH))


@router.post("/watch-pair/start", response_model=WatchPairStartResponse)
async def start_watch_pairing(user: User = Depends(current_active_user)):
    r = await get_redis()
    # NX so a freak collision with another still-live code can't let one
    # code redeem to two different accounts. At a 10^6 key space and a
    # handful of concurrently-live codes this essentially never fires;
    # the retry loop is cheap insurance, not a real bottleneck.
    for _ in range(5):
        code = _generate_code()
        if await r.set(f"watch_pair:{code}", str(user.id), ex=CODE_TTL_SECONDS, nx=True):
            return WatchPairStartResponse(code=code, expires_in=CODE_TTL_SECONDS)
    raise HTTPException(status_code=503, detail="Could not generate a pairing code, try again")


@router.post("/watch-pair/redeem", response_model=WatchPairTokenResponse)
async def redeem_watch_pairing(
    body: WatchPairRedeemRequest,
    session: AsyncSession = Depends(get_async_session),
):
    r = await get_redis()
    key = f"watch_pair:{body.code}"
    user_id = await r.get(key)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired code")
    # One-time use: delete before any further validation so a redeem that
    # fails the is_active check below can't be retried with the same code.
    await r.delete(key)

    user = await session.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired code")

    strategy = get_jwt_strategy()
    token = await strategy.write_token(user)
    return WatchPairTokenResponse(access_token=token, token_type="bearer")
