from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.ownership import get_owned_step, get_owned_task


def create_task(db: Session, task: TaskCreate, step_id: int, owner_id: int) -> Task:
    get_owned_step(db, step_id, owner_id)  # verify ownership of parent step
    db_task = Task(**task.model_dump(), step_id=step_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_tasks_by_step(db: Session, step_id: int, owner_id: int):
    get_owned_step(db, step_id, owner_id)
    return (
        db.query(Task)
        .filter(Task.step_id == step_id)
        .order_by(Task.id.asc())
        .all()
    )


def update_task(db: Session, task_id: int, data: TaskUpdate, owner_id: int) -> Task:
    task = get_owned_task(db, task_id, owner_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: int, owner_id: int) -> None:
    task = get_owned_task(db, task_id, owner_id)
    db.delete(task)
    db.commit()
