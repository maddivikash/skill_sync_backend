from typing import List

from pydantic import BaseModel, Field, constr


class PrepRequest(BaseModel):
    jd_text: constr(min_length=40)  # a real JD, not a word
    days: int = Field(30, ge=7, le=90)  # length of the prep plan


class PrepReply(BaseModel):
    goal_id: int
    role: str
    summary: str            # what this job needs, in two sentences
    readiness: int          # initial 0-100 estimate
    strengths: List[str]    # what the user already has
    gaps: List[str]         # what's missing (the plan targets these)
    total_tasks: int
