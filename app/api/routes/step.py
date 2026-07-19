from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.step import StepCreate, StepOut, StepUpdate
from app.services import step_service

router = APIRouter(prefix="/steps", tags=["Steps"])


@router.post("/path/{path_id}", response_model=StepOut, status_code=status.HTTP_201_CREATED)
def create_step_for_path(path_id: int, step: StepCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return step_service.create_step(db, step, path_id, owner_id=current_user.id)


@router.get("/path/{path_id}", response_model=list[StepOut])
def read_steps_by_path(path_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return step_service.get_steps_by_path(db, path_id, owner_id=current_user.id)


@router.patch("/{step_id}", response_model=StepOut)
def update_step(step_id: int, data: StepUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return step_service.update_step(db, step_id, data, owner_id=current_user.id)


@router.delete("/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step(step_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    step_service.delete_step(db, step_id, owner_id=current_user.id)
