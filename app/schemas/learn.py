from typing import List, Literal

from pydantic import BaseModel, constr


class LearnTask(BaseModel):
    id: int
    title: str
    is_done: bool


class LearnPlanRequest(BaseModel):
    step_id: int


class LearnReplanRequest(BaseModel):
    step_id: int
    instruction: constr(min_length=1, max_length=500)


class LearnPlanReply(BaseModel):
    step_title: str
    category: str  # singular: skill / course / tool / project / topic
    role: str
    tasks: List[LearnTask]


class LearnTurnMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: constr(min_length=1)


class LearnTurnRequest(BaseModel):
    step_id: int
    task_id: int
    mode: Literal["guided", "interactive"]
    messages: List[LearnTurnMessage] = []


class LearnTurnReply(BaseModel):
    reply: str
