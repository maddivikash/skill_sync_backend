"""Minimal email sender for password-reset links.

If SMTP is configured (SMTP_HOST/USER/PASSWORD), send a real email.
Otherwise run in "dev mode": log the link to stdout so the flow works with
zero setup and zero cost. Failures never propagate to the caller (so we don't
leak whether an address exists or whether email delivery worked).
"""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("skillsync.email")


def send_reset_email(to_email: str, reset_link: str) -> None:
    subject = "Reset your Ascend password"
    body = (
        "We received a request to reset your Ascend password.\n\n"
        f"Reset it here (valid for {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes):\n"
        f"{reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )

    # Dev mode — no SMTP configured. Log the link so it's usable for testing.
    if not (settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD):
        print(f"[email:dev] password reset link for {to_email}: {reset_link}", flush=True)
        logger.warning("[email:dev] reset link for %s -> %s", to_email, reset_link)
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to_email
        msg.set_content(body)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
    except Exception as exc:  # never leak delivery details to the client
        logger.error("[email] failed to send reset email to %s: %s", to_email, exc)
