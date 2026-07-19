from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/step/{step_id}", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task_for_step(step_id: int, task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return task_service.create_task(db, task, step_id, owner_id=current_user.id)


@router.get("/step/{step_id}", response_model=list[TaskOut])
def read_tasks_by_step(step_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return task_service.get_tasks_by_step(db, step_id, owner_id=current_user.id)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return task_service.update_task(db, task_id, data, owner_id=current_user.id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task_service.delete_task(db, task_id, owner_id=current_user.id)
