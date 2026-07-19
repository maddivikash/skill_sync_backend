from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.dashboard import Dashboard
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_model=Dashboard)
def get_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return dashboard_service.get_dashboard(db, owner_id=current_user.id)
