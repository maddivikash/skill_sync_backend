from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.catalog import CatalogRoleOut, RoleSuggestions
from app.services import catalog_service

router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/roles", response_model=list[CatalogRoleOut])
def list_roles(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return catalog_service.list_roles(db)


@router.get("/suggestions", response_model=RoleSuggestions)
def get_suggestions(
    role: str = Query("", description="Free-text target role"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return catalog_service.get_suggestions(db, role)
