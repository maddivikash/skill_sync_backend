from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PathBase(BaseModel):
    title: str
    description: Optional[str] = None


class PathCreate(PathBase):
    pass


class PathUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class PathOut(PathBase):
    id: int
    goal_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
