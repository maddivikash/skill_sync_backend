"""Deadline scheduling.

Normal goals: distribute the goal's total window (duration_weeks) across its
steps, weighted by how long each kind of work really takes: courses and
projects get bigger slices than skills and tools.

Dated plans (job prep / rescheduled goals): newly added or regenerated tasks
get due dates spread across the plan's remaining window so nothing is left
undated.
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.learning_path import LearningPath
from app.models.step import Step
from app.models.task import Task

# Relative effort per step by the path it lives in.
_WEIGHTS = (("project", 4.0), ("course", 3.0), ("skill", 1.0), ("tool", 1.0))
_DEFAULT_WEIGHT = 2.0


def _weight_for(path_title: str) -> float:
    t = (path_title or "").lower()
    for key, w in _WEIGHTS:
        if key in t:
            return w
    return _DEFAULT_WEIGHT


def schedule_goal(db: Session, goal: Goal) -> int:
    """(Re)assign due dates to all not-done steps of a goal, weighted by
    category, across duration_weeks from today. Idempotent. Returns the
    number of steps scheduled."""
    paths = (db.query(LearningPath)
             .filter(LearningPath.goal_id == goal.id,
                     LearningPath.is_deleted.is_(False))
             .order_by(LearningPath.id).all())
    weighted = []  # (weight, step)
    for p in paths:
        w = _weight_for(p.title)
        steps = (db.query(Step).filter(Step.path_id == p.id)
                 .order_by(Step.step_order, Step.id).all())
        for s in steps:
            weighted.append((w, s))
    if not weighted:
        return 0

    total_w = sum(w for w, _ in weighted)
    days_total = max(7, goal.duration_weeks * 7)
    start = date.today()
    cum = 0.0
    scheduled = 0
    for w, s in weighted:
        cum += w
        day = max(1, round(days_total * cum / total_w))
        if not s.is_done:
            s.due_date = start + timedelta(days=day)
            scheduled += 1
    db.commit()
    return scheduled


def date_new_tasks(db: Session, goal: Goal, step: Step) -> int:
    """Give due dates to a step's undated tasks by spreading them across the
    plan's remaining window (today -> latest due date in the goal, or the
    goal's duration end). Used after learn plan/replan regenerates tasks."""
    latest = (db.query(Task.due_date)
              .join(Step, Task.step_id == Step.id)
              .join(LearningPath, Step.path_id == LearningPath.id)
              .filter(LearningPath.goal_id == goal.id,
                      Task.due_date.isnot(None))
              .order_by(Task.due_date.desc()).first())
    today = date.today()
    end = latest[0] if latest and latest[0] and latest[0] > today else None
    if end is None:
        end = (step.due_date if step.due_date and step.due_date > today
               else today + timedelta(days=max(7, goal.duration_weeks * 7)))

    undated = [t for t in step.tasks if t.due_date is None and not t.is_done]
    if not undated:
        return 0
    span = max(1, (end - today).days)
    n = len(undated)
    for i, t in enumerate(undated, start=1):
        t.due_date = today + timedelta(days=max(1, round(span * i / n)))
    db.commit()
    return n
