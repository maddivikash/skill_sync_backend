"""Ownership resolution helpers.

Every nested resource (path/step/task) is owned transitively through its
Goal.owner_id. These helpers load a resource *and* verify the current user
owns it, raising 404 otherwise (404 rather than 403 so we don't leak the
existence of other users' resources).
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.learning_path import LearningPath
from app.models.step import Step
from app.models.task import Task


def _not_found(name: str):
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found"
    )


def get_owned_goal(db: Session, goal_id: int, user_id: int) -> Goal:
    goal = (
        db.query(Goal)
        .filter(
            Goal.id == goal_id,
            Goal.owner_id == user_id,
            Goal.is_deleted.is_(False),
        )
        .first()
    )
    if not goal:
        raise _not_found("Goal")
    return goal


def get_owned_path(db: Session, path_id: int, user_id: int) -> LearningPath:
    path = (
        db.query(LearningPath)
        .join(Goal, LearningPath.goal_id == Goal.id)
        .filter(
            LearningPath.id == path_id,
            LearningPath.is_deleted.is_(False),
            Goal.owner_id == user_id,
            Goal.is_deleted.is_(False),
        )
        .first()
    )
    if not path:
        raise _not_found("Path")
    return path


def get_owned_step(db: Session, step_id: int, user_id: int) -> Step:
    step = (
        db.query(Step)
        .join(LearningPath, Step.path_id == LearningPath.id)
        .join(Goal, LearningPath.goal_id == Goal.id)
        .filter(
            Step.id == step_id,
            LearningPath.is_deleted.is_(False),
            Goal.owner_id == user_id,
            Goal.is_deleted.is_(False),
        )
        .first()
    )
    if not step:
        raise _not_found("Step")
    return step


def get_owned_task(db: Session, task_id: int, user_id: int) -> Task:
    task = (
        db.query(Task)
        .join(Step, Task.step_id == Step.id)
        .join(LearningPath, Step.path_id == LearningPath.id)
        .join(Goal, LearningPath.goal_id == Goal.id)
        .filter(
            Task.id == task_id,
            LearningPath.is_deleted.is_(False),
            Goal.owner_id == user_id,
            Goal.is_deleted.is_(False),
        )
        .first()
    )
    if not task:
        raise _not_found("Task")
    return task
