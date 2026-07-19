from typing import List

from pydantic import BaseModel

from app.schemas.goal import GoalOut


class ProgressStats(BaseModel):
    total_tasks: int
    done_tasks: int
    percent: float


class GoalWithProgress(GoalOut):
    paths_count: int
    progress: ProgressStats


class Dashboard(BaseModel):
    overall: ProgressStats
    goals: List[GoalWithProgress]
