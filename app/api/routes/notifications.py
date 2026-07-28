"""In-app notifications: due-today and overdue items, derived live from the
user's dated steps and tasks (same source the reminder emails use)."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.goal import Goal
from app.models.learning_path import LearningPath
from app.models.step import Step
from app.models.task import Task
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def list_notifications(db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    today = date.today()
    items = []

    step_rows = (db.query(Step, Goal)
                 .join(LearningPath, Step.path_id == LearningPath.id)
                 .join(Goal, LearningPath.goal_id == Goal.id)
                 .filter(Goal.owner_id == current_user.id,
                         Goal.is_deleted.is_(False),
                         Goal.is_archived.is_(False),
                         LearningPath.is_deleted.is_(False),
                         Step.is_done.is_(False),
                         Step.due_date.isnot(None),
                         Step.due_date <= today)
                 .all())
    for step, goal in step_rows:
        items.append({"kind": "step", "title": step.title, "goal_id": goal.id,
                      "goal_role": goal.role, "due_date": step.due_date.isoformat(),
                      "overdue": step.due_date < today})

    task_rows = (db.query(Task, Goal)
                 .join(Step, Task.step_id == Step.id)
                 .join(LearningPath, Step.path_id == LearningPath.id)
                 .join(Goal, LearningPath.goal_id == Goal.id)
                 .filter(Goal.owner_id == current_user.id,
                         Goal.is_deleted.is_(False),
                         Goal.is_archived.is_(False),
                         LearningPath.is_deleted.is_(False),
                         Task.is_done.is_(False),
                         Task.due_date.isnot(None),
                         Task.due_date <= today)
                 .all())
    for task, goal in task_rows:
        items.append({"kind": "task", "title": task.title, "goal_id": goal.id,
                      "goal_role": goal.role, "due_date": task.due_date.isoformat(),
                      "overdue": task.due_date < today})

    # due-today first, then overdue (oldest last), stable by title
    items.sort(key=lambda x: (x["overdue"], x["due_date"], x["title"]))
    return {"items": items, "count": len(items)}
