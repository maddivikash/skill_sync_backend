from sqlalchemy.orm import Session

from app.models.learning_path import LearningPath
from app.schemas.path import PathCreate, PathUpdate
from app.services.ownership import get_owned_goal, get_owned_path


def create_path(db: Session, path_data: PathCreate, goal_id: int, owner_id: int) -> LearningPath:
    get_owned_goal(db, goal_id, owner_id)  # verify ownership of parent goal
    path = LearningPath(**path_data.model_dump(), goal_id=goal_id)
    db.add(path)
    db.commit()
    db.refresh(path)
    return path


def get_paths_by_goal(db: Session, goal_id: int, owner_id: int):
    get_owned_goal(db, goal_id, owner_id)
    return (
        db.query(LearningPath)
        .filter(
            LearningPath.goal_id == goal_id,
            LearningPath.is_deleted.is_(False),
        )
        .order_by(LearningPath.created_at.asc())
        .all()
    )


def update_path(db: Session, path_id: int, data: PathUpdate, owner_id: int) -> LearningPath:
    path = get_owned_path(db, path_id, owner_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(path, field, value)
    db.commit()
    db.refresh(path)
    return path


def delete_path(db: Session, path_id: int, owner_id: int) -> None:
    path = get_owned_path(db, path_id, owner_id)
    path.is_deleted = True
    db.commit()
