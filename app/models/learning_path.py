from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id          = Column(Integer, primary_key=True, index=True)
    goal_id     = Column(Integer, ForeignKey("goals.id"), index=True, nullable=False)
    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_deleted  = Column(Boolean, default=False, index=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    goal  = relationship("Goal", back_populates="learning_paths")
    steps = relationship(
        "Step", back_populates="path", cascade="all, delete-orphan",
        order_by="Step.step_order",
    )
