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


def _reset_html(reset_link: str, minutes: int) -> str:
    """Warm, branded HTML matching the Ascend theme. Table + inline styles for
    email-client compatibility (Gmail/Outlook strip <style> and fl/grid)."""
    return f"""\
<!doctype html>
<html>
<body style="margin:0;padding:0;background:#f4efe4;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:#f4efe4;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="max-width:480px;background:#ffffff;border-radius:16px;
                    overflow:hidden;border:1px solid #e7ddc9;">
        <tr><td style="padding:32px 36px 8px 36px;">
          <table role="presentation" cellpadding="0" cellspacing="0">
            <tr>
              <td style="width:34px;height:34px;background:#a8492f;border-radius:9px;
                         text-align:center;vertical-align:middle;color:#fff;
                         font-family:Georgia,serif;font-size:18px;font-weight:bold;">A</td>
              <td style="padding-left:10px;font-family:Georgia,'Times New Roman',serif;
                         font-size:20px;color:#1b1510;font-weight:bold;">Ascend</td>
            </tr>
          </table>
        </td></tr>
        <tr><td style="padding:20px 36px 0 36px;">
          <h1 style="margin:0 0 14px 0;font-family:Georgia,'Times New Roman',serif;
                     font-size:24px;line-height:1.25;color:#1b1510;">
            Reset your password
          </h1>
          <p style="margin:0 0 22px 0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
                    font-size:15px;line-height:1.6;color:#5c5347;">
            We received a request to reset your Ascend password. Click the button
            below to choose a new one.
          </p>
        </td></tr>
        <tr><td align="center" style="padding:0 36px;">
          <table role="presentation" cellpadding="0" cellspacing="0">
            <tr><td style="border-radius:999px;background:#a8492f;">
              <a href="{reset_link}"
                 style="display:inline-block;padding:14px 34px;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
                        font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;
                        border-radius:999px;">Reset password</a>
            </td></tr>
          </table>
        </td></tr>
        <tr><td style="padding:20px 36px 4px 36px;">
          <p style="margin:0 0 20px 0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
                    font-size:13px;line-height:1.6;color:#8a7f6f;text-align:center;">
            This link is valid for {minutes} minutes.
          </p>
        </td></tr>
        <tr><td style="padding:0 36px 32px 36px;border-top:1px solid #efe7d6;">
          <p style="margin:18px 0 0 0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
                    font-size:12px;line-height:1.6;color:#a89e8c;">
            If you didn't request this, you can safely ignore this email. Your
            password will stay the same.
          </p>
        </td></tr>
      </table>
      <p style="max-width:480px;margin:16px auto 0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
                font-size:11px;color:#b3a894;text-align:center;">
        Ascend · your learning goals, on track
      </p>
    </td></tr>
  </table>
</body>
</html>"""


def send_reset_email(to_email: str, reset_link: str) -> None:
    minutes = settings.RESET_TOKEN_EXPIRE_MINUTES
    subject = "Reset your Ascend password"
    text_body = (
        "We received a request to reset your Ascend password.\n\n"
        f"Reset it here (valid for {minutes} minutes):\n"
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
        msg.set_content(text_body)  # plain-text fallback
        msg.add_alternative(_reset_html(reset_link, minutes), subtype="html")
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
    except Exception as exc:  # never leak delivery details to the client
        logger.error("[email] failed to send reset email to %s: %s", to_email, exc)
