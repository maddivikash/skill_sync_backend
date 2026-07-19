from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StepBase(BaseModel):
    title: str
    description: Optional[str] = None
    step_order: int = 0


class StepCreate(StepBase):
    pass


class StepUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    step_order: Optional[int] = None
    is_done: Optional[bool] = None


class StepOut(StepBase):
    id: int
    path_id: int
    is_done: bool
    created_at: datetime

    model_config = {"from_attributes": True}
