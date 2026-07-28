from typing import List, Optional

from pydantic import BaseModel

from app.schemas.goal import GoalOut


class ProgressStats(BaseModel):
    total_tasks: int
    done_tasks: int
    percent: float


class GoalWithProgress(GoalOut):
    paths_count: int
    progress: ProgressStats
    readiness: Optional[int] = None  # job-prep goals: current readiness 0-100


class Dashboard(BaseModel):
    overall: ProgressStats
    goals: List[GoalWithProgress]
