from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalOut, GoalUpdate
from app.services import goal_service

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.post("/", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(goal: GoalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return goal_service.create_goal(db, goal, owner_id=current_user.id)


@router.get("/", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return goal_service.get_all_goals(db, owner_id=current_user.id)


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(goal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return goal_service.get_goal(db, goal_id, owner_id=current_user.id)


@router.put("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, data: GoalUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return goal_service.update_goal(db, goal_id, data, owner_id=current_user.id)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    goal_service.delete_goal(db, goal_id, owner_id=current_user.id)


@router.post("/{goal_id}/reset", response_model=dict)
def reset_goal(goal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    removed = goal_service.reset_goal(db, goal_id, owner_id=current_user.id)
    return {"message": f"Removed {removed} paths and all their content."}
