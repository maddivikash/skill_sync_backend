from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class CatalogRole(Base):
    """A target role users can pick (e.g. "Backend Engineer")."""

    __tablename__ = "catalog_roles"

    id         = Column(Integer, primary_key=True, index=True)
    slug       = Column(String(80), unique=True, index=True, nullable=False)
    name       = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship(
        "CatalogItem", back_populates="role", cascade="all, delete-orphan",
        order_by="CatalogItem.sort_order",
    )


class CatalogItem(Base):
    """A suggestion under a role: a skill, course, tool, or project."""

    __tablename__ = "catalog_items"

    id              = Column(Integer, primary_key=True, index=True)
    role_id         = Column(Integer, ForeignKey("catalog_roles.id"), index=True, nullable=False)
    category        = Column(String(20), index=True, nullable=False)  # skill|course|tool|project
    name            = Column(String(200), nullable=False)
    description     = Column(Text, nullable=True)
    provider        = Column(String(120), nullable=True)   # e.g. "Coursera" (courses)
    url             = Column(String(500), nullable=True)    # course link
    estimated_hours = Column(Integer, nullable=True)        # course/effort estimate
    steps           = Column(JSON, nullable=True)           # project milestones (list[str])
    sort_order      = Column(Integer, default=0)

    role = relationship("CatalogRole", back_populates="items")
