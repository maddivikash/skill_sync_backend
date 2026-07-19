from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.learning_path import LearningPath
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.ownership import get_owned_goal


def create_goal(db: Session, goal_data: GoalCreate, owner_id: int) -> Goal:
    goal = Goal(**goal_data.model_dump(), owner_id=owner_id)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def get_goal(db: Session, goal_id: int, owner_id: int) -> Goal:
    return get_owned_goal(db, goal_id, owner_id)


def get_all_goals(db: Session, owner_id: int):
    return (
        db.query(Goal)
        .filter(Goal.owner_id == owner_id, Goal.is_deleted.is_(False))
        .order_by(Goal.created_at.desc())
        .all()
    )


def update_goal(db: Session, goal_id: int, data: GoalUpdate, owner_id: int) -> Goal:
    goal = get_owned_goal(db, goal_id, owner_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal_id: int, owner_id: int) -> None:
    goal = get_owned_goal(db, goal_id, owner_id)
    goal.is_deleted = True  # soft delete
    db.commit()


def reset_goal(db: Session, goal_id: int, owner_id: int) -> int:
    """Remove all learning paths (and their steps/tasks) under a goal, keeping the goal."""
    goal = get_owned_goal(db, goal_id, owner_id)
    paths = db.query(LearningPath).filter(LearningPath.goal_id == goal.id).all()
    count = len(paths)
    for p in paths:
        db.delete(p)  # cascade removes steps -> tasks
    db.commit()
    return count
