"""System transactional email — currently just password-reset links (see
UserManager.on_after_forgot_password / on_after_reset_password in
app/core/auth.py). Plain smtplib, same approach email_imap_service.py
already uses for per-user mailboxes — just pointed at the app's own relay
account (SMTP_* settings) instead of a user's connected inbox.

Blank SMTP_HOST means "not configured": send_email() logs and returns
False instead of raising, so the reset endpoint still works (the token is
generated either way) — it just has nowhere to deliver the link.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _send_sync(*, to: str, subject: str, html_body: str, text_body: str) -> None:
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    host, port = settings.smtp_host, settings.smtp_port
    # 465 is always implicit SSL (Hostinger, Gmail, most providers);
    # smtp_use_tls only matters for the STARTTLS ports (587/25).
    use_ssl = port == 465
    client: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=20) if use_ssl else smtplib.SMTP(host, port, timeout=20)
    try:
        if not use_ssl and settings.smtp_use_tls:
            client.starttls()
        client.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        client.send_message(msg)
    finally:
        try:
            client.quit()
        except Exception:
            pass


async def send_email(*, to: str, subject: str, html_body: str, text_body: str) -> bool:
    """Returns True once sent, False if SMTP isn't configured or the send
    failed (always logged, never raised — email delivery is best-effort,
    it must never break the request that triggered it)."""
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_user:
        logger.warning("SMTP not configured (SMTP_HOST/SMTP_USER blank) — skipping email to %s: %s", to, subject)
        return False
    try:
        await asyncio.to_thread(_send_sync, to=to, subject=subject, html_body=html_body, text_body=text_body)
        return True
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        logger.error("Failed to send email to %s (%s): %s", to, subject, exc)
        return False
