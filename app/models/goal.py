from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
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
    is_archived    = Column(Boolean, default=False, index=True)
    is_deleted     = Column(Boolean, default=False, index=True)
    # Job-prep goals: the pasted job description and the LLM's initial
    # readiness estimate (0-100). Current readiness is derived from progress.
    jd_text        = Column(Text, nullable=True)
    readiness_base = Column(Integer, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    learning_paths = relationship(
        "LearningPath", back_populates="goal", cascade="all, delete-orphan"
    )
