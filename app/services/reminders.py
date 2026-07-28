"""Daily task reminders: email each user their due-today and overdue tasks.

Run inside the api container (host cron calls this once a day):
    python -m app.services.reminders

Only emails users who actually have something due; skips silently when SMTP
is not configured. This is the accountability loop ChatGPT doesn't have.
"""
import logging
import smtplib
from datetime import date
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.goal import Goal
from app.models.learning_path import LearningPath
from app.models.step import Step
from app.models.task import Task
from app.models.user import User

logger = logging.getLogger("skillsync.reminders")


def _due_by_user(db: Session):
    """{user: [(goal_role, item_title, due_date), ...]} for open dated tasks
    AND steps (weighted step deadlines from normal goals count too)."""
    base_filters = [Goal.is_deleted.is_(False),
                    Goal.is_archived.is_(False),
                    LearningPath.is_deleted.is_(False)]
    task_rows = (db.query(User, Goal.role, Task.title, Task.due_date)
                 .join(Goal, Goal.owner_id == User.id)
                 .join(LearningPath, LearningPath.goal_id == Goal.id)
                 .join(Step, Step.path_id == LearningPath.id)
                 .join(Task, Task.step_id == Step.id)
                 .filter(*base_filters,
                         Task.is_done.is_(False),
                         Task.due_date.isnot(None),
                         Task.due_date <= date.today())
                 .all())
    step_rows = (db.query(User, Goal.role, Step.title, Step.due_date)
                 .join(Goal, Goal.owner_id == User.id)
                 .join(LearningPath, LearningPath.goal_id == Goal.id)
                 .join(Step, Step.path_id == LearningPath.id)
                 .filter(*base_filters,
                         Step.is_done.is_(False),
                         Step.due_date.isnot(None),
                         Step.due_date <= date.today())
                 .all())
    by_user = {}
    for user, role, title, due in list(task_rows) + list(step_rows):
        if not user.email_reminders:
            continue  # user turned daily emails off
        by_user.setdefault(user, []).append((role, title, due))
    return by_user


def _rows_html(rows, color) -> str:
    out = []
    for role, title, extra in rows:
        out.append(
            f'<tr><td style="padding:9px 0;border-bottom:1px solid #efe7d6;">'
            f'<span style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
            f'font-size:14px;color:#1b1510;">{title}</span><br>'
            f'<span style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
            f'font-size:12px;color:{color};">{role}{extra}</span></td></tr>')
    return "".join(out)


def _email_body(items) -> tuple:
    today = date.today()
    overdue = [(r, t, d) for r, t, d in items if d < today]
    due_now = [(r, t, d) for r, t, d in items if d == today]

    # Plain-text fallback
    lines = ["Here's your Ascend check-in.\n"]
    if due_now:
        lines.append("Due today:")
        lines += [f"  - {t}  ({r})" for r, t, _ in due_now]
        lines.append("")
    if overdue:
        lines.append("Still open (past due):")
        lines += [f"  - {t}  ({r}, was due {d.strftime('%b %d')})" for r, t, d in overdue]
        lines.append("")
    lines.append("Open your plan: " + settings.FRONTEND_URL)
    lines.append("\nSmall steps count. See you in there.")
    text = "\n".join(lines)

    n = len(due_now)
    subject = (f"{n} task{'s' if n != 1 else ''} due today on Ascend"
               if due_now else "You have open tasks on Ascend")

    # Branded HTML (same warm look as the reset email)
    sections = ""
    if due_now:
        sections += (
            '<p style="margin:18px 0 4px;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
            'font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:#a8492f;">Due today</p>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            + _rows_html([(r, t, "") for r, t, _ in due_now], "#8a7f6f")
            + "</table>")
    if overdue:
        sections += (
            '<p style="margin:18px 0 4px;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
            'font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:#b3432b;">Still open (past due)</p>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            + _rows_html([(r, t, f" · was due {d.strftime('%b %d')}") for r, t, d in overdue], "#b3432b")
            + "</table>")

    html = f"""\
<!doctype html>
<html>
<body style="margin:0;padding:0;background:#f4efe4;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:#f4efe4;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="max-width:480px;background:#ffffff;border-radius:16px;overflow:hidden;
                    border:1px solid #e7ddc9;">
        <tr><td style="padding:28px 34px 6px 34px;">
          <table role="presentation" cellpadding="0" cellspacing="0"><tr>
            <td style="width:32px;height:32px;background:#a8492f;border-radius:8px;text-align:center;
                       vertical-align:middle;color:#fff;font-family:Georgia,serif;font-size:17px;
                       font-weight:bold;">A</td>
            <td style="padding-left:10px;font-family:Georgia,'Times New Roman',serif;font-size:19px;
                       color:#1b1510;font-weight:bold;">Ascend</td>
          </tr></table>
        </td></tr>
        <tr><td style="padding:16px 34px 0 34px;">
          <h1 style="margin:0 0 6px;font-family:Georgia,'Times New Roman',serif;font-size:22px;
                     line-height:1.25;color:#1b1510;">Your check-in for today</h1>
          <p style="margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
                    font-size:14px;line-height:1.6;color:#5c5347;">
            Small steps count. Here's what's on your plate.</p>
          {sections}
        </td></tr>
        <tr><td align="center" style="padding:24px 34px 28px;">
          <table role="presentation" cellpadding="0" cellspacing="0">
            <tr><td style="border-radius:999px;background:#a8492f;">
              <a href="{settings.FRONTEND_URL}"
                 style="display:inline-block;padding:12px 30px;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
                        font-size:14px;font-weight:600;color:#ffffff;text-decoration:none;
                        border-radius:999px;">Open my plan</a>
            </td></tr>
          </table>
        </td></tr>
      </table>
      <p style="max-width:480px;margin:14px auto 0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
                font-size:11px;color:#b3a894;text-align:center;">
        You can turn these off in Profile and settings on Ascend.</p>
    </td></tr>
  </table>
</body>
</html>"""
    return subject, text, html


def send_due_reminders() -> int:
    """Send reminder emails. Returns how many were sent."""
    if not (settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD):
        logger.warning("[reminders] SMTP not configured; skipping")
        return 0

    db = SessionLocal()
    sent = 0
    try:
        for user, items in _due_by_user(db).items():
            subject, text, html = _email_body(items)
            try:
                msg = EmailMessage()
                msg["Subject"] = subject
                msg["From"] = settings.EMAIL_FROM
                msg["To"] = user.email
                msg.set_content(text)
                msg.add_alternative(html, subtype="html")
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT,
                                  timeout=15) as smtp:
                    smtp.starttls()
                    smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    smtp.send_message(msg)
                sent += 1
            except Exception as exc:
                # One bad address must not stop the rest.
                logger.error("[reminders] failed for %s: %s", user.email, exc)
    finally:
        db.close()
    logger.info("[reminders] sent %d reminder(s)", sent)
    return sent


if __name__ == "__main__":
    print(f"[reminders] sent {send_due_reminders()} reminder(s)", flush=True)
