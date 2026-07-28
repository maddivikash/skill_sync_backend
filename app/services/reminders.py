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
    """{user: [(goal_role, task_title, due_date), ...]} for open dated tasks."""
    rows = (db.query(User, Goal.role, Task.title, Task.due_date)
            .join(Goal, Goal.owner_id == User.id)
            .join(LearningPath, LearningPath.goal_id == Goal.id)
            .join(Step, Step.path_id == LearningPath.id)
            .join(Task, Task.step_id == Step.id)
            .filter(Goal.is_deleted.is_(False),
                    Goal.is_archived.is_(False),
                    LearningPath.is_deleted.is_(False),
                    Task.is_done.is_(False),
                    Task.due_date.isnot(None),
                    Task.due_date <= date.today())
            .all())
    by_user = {}
    for user, role, title, due in rows:
        by_user.setdefault(user, []).append((role, title, due))
    return by_user


def _email_body(items) -> tuple:
    today = date.today()
    overdue = [(r, t, d) for r, t, d in items if d < today]
    due_now = [(r, t, d) for r, t, d in items if d == today]

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
    return subject, text


def send_due_reminders() -> int:
    """Send reminder emails. Returns how many were sent."""
    if not (settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD):
        logger.warning("[reminders] SMTP not configured; skipping")
        return 0

    db = SessionLocal()
    sent = 0
    try:
        for user, items in _due_by_user(db).items():
            subject, text = _email_body(items)
            try:
                msg = EmailMessage()
                msg["Subject"] = subject
                msg["From"] = settings.EMAIL_FROM
                msg["To"] = user.email
                msg.set_content(text)
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
