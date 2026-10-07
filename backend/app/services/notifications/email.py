"""Minimal SMTP notification sender (dev: caught by Mailhog, never a real
inbox). Failures are logged, never raised — a notification bug must not
block the workflow it's attached to (approval, escalation, etc.).
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_email(to_addrs: list[str], subject: str, body: str) -> None:
    if not to_addrs:
        return

    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(to_addrs)
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as smtp:
            smtp.send_message(message)
    except Exception:
        logger.exception("Failed to send notification email: %s", subject)
