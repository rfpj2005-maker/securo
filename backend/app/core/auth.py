import uuid
from decimal import Decimal
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.user import User

settings = get_settings()


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    user_db: SQLAlchemyUserDatabase
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")
        # If request is None, this was called programmatically (e.g., from setup endpoint)
        # which handles wallet creation, categories, and rules itself.
        if request is None:
            return
        # Create default wallet for users registered via /auth/register.
        from app.models.account import Account
        from app.services.category_service import create_default_categories
        from app.services.rule_service import create_default_rules
        from app.services.workspace_service import create_personal_workspace_for_user

        session = self.user_db.session
        currency = user.primary_currency
        lang = (user.preferences or {}).get("language", "en")

        # Every new user gets a Personal workspace + owner membership.
        # All their seeded data (wallet, categories, rules) reparent to it.
        workspace = await create_personal_workspace_for_user(session, user)

        wallet_name = "Carteira" if lang.startswith("pt") else "Wallet"
        wallet = Account(
            user_id=user.id,
            workspace_id=workspace.id,
            name=wallet_name,
            type="checking",
            balance=Decimal("0.00"),
            currency=currency,
        )
        session.add(wallet)
        await session.commit()

        # Create default categories and rules for the new user
        await create_default_categories(session, user.id, lang, workspace_id=workspace.id)
        await create_default_rules(session, user.id, lang, workspace_id=workspace.id)

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        from app.services.mailer import send_email

        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        lang = (user.preferences or {}).get("language", "en")
        if lang.startswith("pt"):
            subject = "Redefinir sua senha — Bússola"
            text = (
                "Recebemos um pedido para redefinir a senha da sua conta Bússola.\n\n"
                f"Escolha uma nova senha aqui (link válido por 1 hora):\n{reset_url}\n\n"
                "Se você não pediu isso, pode ignorar este e-mail — sua senha continua a mesma."
            )
            html = (
                "<p>Recebemos um pedido para redefinir a senha da sua conta Bússola.</p>"
                f'<p><a href="{reset_url}">Clique aqui para escolher uma nova senha</a> (o link vale por 1 hora).</p>'
                "<p>Se você não pediu isso, pode ignorar este e-mail — sua senha continua a mesma.</p>"
            )
        else:
            subject = "Reset your password — Bússola"
            text = (
                "We received a request to reset your Bússola account password.\n\n"
                f"Choose a new password here (link valid for 1 hour):\n{reset_url}\n\n"
                "If you didn't request this, you can ignore this email — your password stays the same."
            )
            html = (
                "<p>We received a request to reset your Bússola account password.</p>"
                f'<p><a href="{reset_url}">Click here to choose a new password</a> (the link is valid for 1 hour).</p>'
                "<p>If you didn't request this, you can ignore this email — your password stays the same.</p>"
            )
        sent = await send_email(to=user.email, subject=subject, html_body=html, text_body=text)
        if not sent:
            # SMTP not configured (or the send failed) — still log the link
            # server-side so it's recoverable from `docker compose logs`.
            print(f"[password-reset] could not email {user.id} ({user.email}) — reset link: {reset_url}")

    async def on_after_reset_password(self, user: User, request: Optional[Request] = None):
        from app.services.mailer import send_email

        lang = (user.preferences or {}).get("language", "en")
        if lang.startswith("pt"):
            subject = "Sua senha foi alterada — Bússola"
            text = "A senha da sua conta Bússola foi alterada agora há pouco. Se não foi você, entre em contato imediatamente."
        else:
            subject = "Your password was changed — Bússola"
            text = "Your Bússola account password was just changed. If this wasn't you, contact support immediately."
        await send_email(to=user.email, subject=subject, html_body=f"<p>{text}</p>", text_body=text)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="api/auth/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.secret_key.get_secret_value(),
        lifetime_seconds=settings.access_token_expire_minutes * 60,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
