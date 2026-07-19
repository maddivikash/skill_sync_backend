from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.learning_path import LearningPath
from app.models.step import Step
from app.models.task import Task


def _stats(total: int, done: int) -> dict:
    percent = round((done / total) * 100, 1) if total else 0.0
    return {"total_tasks": total, "done_tasks": done, "percent": percent}


def _task_counts_by_goal(db: Session, owner_id: int) -> dict:
    """Return {goal_id: (total_tasks, done_tasks)} across non-deleted paths."""
    rows = (
        db.query(
            Goal.id.label("goal_id"),
            func.count(Task.id).label("total"),
            func.coalesce(func.sum(cast(Task.is_done, Integer)), 0).label("done"),
        )
        .outerjoin(
            LearningPath,
            (LearningPath.goal_id == Goal.id) & (LearningPath.is_deleted.is_(False)),
        )
        .outerjoin(Step, Step.path_id == LearningPath.id)
        .outerjoin(Task, Task.step_id == Step.id)
        .filter(Goal.owner_id == owner_id, Goal.is_deleted.is_(False))
        .group_by(Goal.id)
        .all()
    )
    return {r.goal_id: (int(r.total), int(r.done)) for r in rows}


def _paths_count_by_goal(db: Session, owner_id: int) -> dict:
    rows = (
        db.query(LearningPath.goal_id, func.count(LearningPath.id))
        .join(Goal, Goal.id == LearningPath.goal_id)
        .filter(
            Goal.owner_id == owner_id,
            Goal.is_deleted.is_(False),
            LearningPath.is_deleted.is_(False),
        )
        .group_by(LearningPath.goal_id)
        .all()
    )
    return {gid: cnt for gid, cnt in rows}


def get_dashboard(db: Session, owner_id: int) -> dict:
    goals = (
        db.query(Goal)
        .filter(Goal.owner_id == owner_id, Goal.is_deleted.is_(False))
        .order_by(Goal.created_at.desc())
        .all()
    )
    counts = _task_counts_by_goal(db, owner_id)
    paths_count = _paths_count_by_goal(db, owner_id)

    overall_total = 0
    overall_done = 0
    goal_items = []
    for goal in goals:
        total, done = counts.get(goal.id, (0, 0))
        overall_total += total
        overall_done += done
        goal_items.append(
            {
                "id": goal.id,
                "role": goal.role,
                "hours_per_week": goal.hours_per_week,
                "duration_weeks": goal.duration_weeks,
                "is_active": goal.is_active,
                "created_at": goal.created_at,
                "paths_count": paths_count.get(goal.id, 0),
                "progress": _stats(total, done),
            }
        )

    return {"overall": _stats(overall_total, overall_done), "goals": goal_items}
