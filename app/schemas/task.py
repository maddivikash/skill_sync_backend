from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None


class TaskCreate(TaskBase):
    due_date: Optional[date] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_done: Optional[bool] = None
    due_date: Optional[date] = None


class TaskOut(TaskBase):
    id: int
    step_id: int
    is_done: bool
    due_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}
