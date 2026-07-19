from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    role: str = Field(..., max_length=100)
    hours_per_week: int = Field(..., gt=0, le=168)
    duration_weeks: int = Field(..., gt=0, le=520)


class GoalUpdate(BaseModel):
    role: Optional[str] = Field(None, max_length=100)
    hours_per_week: Optional[int] = Field(None, gt=0, le=168)
    duration_weeks: Optional[int] = Field(None, gt=0, le=520)
    is_active: Optional[bool] = None


class GoalOut(BaseModel):
    id: int
    role: str
    hours_per_week: int
    duration_weeks: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
