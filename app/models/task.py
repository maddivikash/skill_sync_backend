from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Task(Base):
    __tablename__ = "tasks"

    id          = Column(Integer, primary_key=True, index=True)
    step_id     = Column(Integer, ForeignKey("steps.id"), index=True, nullable=False)
    title       = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    is_done     = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    step = relationship("Step", back_populates="tasks")
