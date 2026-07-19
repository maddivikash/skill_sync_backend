from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Step(Base):
    __tablename__ = "steps"

    id          = Column(Integer, primary_key=True, index=True)
    path_id     = Column(Integer, ForeignKey("learning_paths.id"), index=True, nullable=False)
    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    step_order  = Column(Integer, default=0)   # `order` is reserved in SQL
    is_done     = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    path  = relationship("LearningPath", back_populates="steps")
    tasks = relationship(
        "Task", back_populates="step", cascade="all, delete-orphan",
        order_by="Task.id",
    )
