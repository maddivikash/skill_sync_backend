from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.path import PathCreate, PathOut, PathUpdate
from app.services import path_service

router = APIRouter(prefix="/paths", tags=["Paths"])


@router.post("/{goal_id}", response_model=PathOut, status_code=status.HTTP_201_CREATED)
def create_path(goal_id: int, path: PathCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return path_service.create_path(db, path, goal_id, owner_id=current_user.id)


@router.get("/goal/{goal_id}", response_model=list[PathOut])
def get_paths(goal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return path_service.get_paths_by_goal(db, goal_id, owner_id=current_user.id)


@router.put("/{path_id}", response_model=PathOut)
def update_path(path_id: int, data: PathUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return path_service.update_path(db, path_id, data, owner_id=current_user.id)


@router.delete("/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_path(path_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    path_service.delete_path(db, path_id, owner_id=current_user.id)
