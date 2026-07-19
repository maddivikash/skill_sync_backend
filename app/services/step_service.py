from sqlalchemy.orm import Session

from app.models.step import Step
from app.schemas.step import StepCreate, StepUpdate
from app.services.ownership import get_owned_path, get_owned_step


def create_step(db: Session, step: StepCreate, path_id: int, owner_id: int) -> Step:
    get_owned_path(db, path_id, owner_id)  # verify ownership of parent path
    db_step = Step(**step.model_dump(), path_id=path_id)
    db.add(db_step)
    db.commit()
    db.refresh(db_step)
    return db_step


def get_steps_by_path(db: Session, path_id: int, owner_id: int):
    get_owned_path(db, path_id, owner_id)
    return (
        db.query(Step)
        .filter(Step.path_id == path_id)
        .order_by(Step.step_order.asc(), Step.id.asc())
        .all()
    )


def update_step(db: Session, step_id: int, data: StepUpdate, owner_id: int) -> Step:
    step = get_owned_step(db, step_id, owner_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(step, field, value)
    db.commit()
    db.refresh(step)
    return step


def delete_step(db: Session, step_id: int, owner_id: int) -> None:
    step = get_owned_step(db, step_id, owner_id)
    db.delete(step)
    db.commit()
