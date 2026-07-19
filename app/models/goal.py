from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Goal(Base):
    __tablename__ = "goals"

    id             = Column(Integer, primary_key=True, index=True)
    owner_id       = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    role           = Column(String(100), index=True, nullable=False)
    hours_per_week = Column(Integer, nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    is_active      = Column(Boolean, default=True)
    is_deleted     = Column(Boolean, default=False, index=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    learning_paths = relationship(
        "LearningPath", back_populates="goal", cascade="all, delete-orphan"
    )
