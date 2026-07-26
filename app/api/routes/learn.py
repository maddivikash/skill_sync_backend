"""Learn Studio: the coach breaks a step (skill/course/tool/project) into a
task list, then tutors the user through the tasks one at a time.

Two endpoints:
  POST /learn/plan  -> generate (or return existing) tasks for a step
  POST /learn/turn  -> one tutoring turn for a specific task (guided/interactive)

Everything is ownership-scoped: a user can only learn their own steps.
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.goal import Goal
from app.models.learning_path import LearningPath
from app.models.step import Step
from app.models.task import Task
from app.models.user import User
from app.schemas.learn import (
    LearnPlanReply,
    LearnPlanRequest,
    LearnTurnReply,
    LearnTurnRequest,
)
from app.services import groq_client

router = APIRouter(prefix="/learn", tags=["Learn"])
logger = logging.getLogger("skillsync.learn")


def _owned_step(db: Session, uid: int, sid: int):
    """Return (step, path, goal) if the step belongs to the user, else None."""
    row = (db.query(Step, LearningPath, Goal)
           .join(LearningPath, Step.path_id == LearningPath.id)
           .join(Goal, LearningPath.goal_id == Goal.id)
           .filter(Step.id == sid, Goal.owner_id == uid,
                   Goal.is_deleted == False).first())  # noqa: E712
    return row  # (Step, LearningPath, Goal) or None


# Map a path title like "Skills"/"Courses" to a singular noun for the prompt.
def _category(path_title: str) -> str:
    t = (path_title or "").strip().lower()
    for plural, singular in (("skills", "skill"), ("courses", "course"),
                             ("tools", "tool"), ("projects", "project")):
        if plural in t or t == singular:
            return singular
    return "topic"


@router.post("/plan", response_model=LearnPlanReply)
def make_plan(req: LearnPlanRequest, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    row = _owned_step(db, current_user.id, req.step_id)
    if not row:
        raise HTTPException(status_code=404, detail="Step not found")
    step, path, goal = row
    category = _category(path.title)

    # Resume: if this step already has tasks, reuse them (don't regenerate).
    if step.tasks:
        tasks = step.tasks
    else:
        prompt = (
            f"Break the {category} \"{step.title}\" into 4 to 6 concrete, ordered "
            f"learning tasks for someone working toward becoming a {goal.role}. "
            f"Each task is one focused thing to learn or practice, in a logical "
            f"order. Keep each title short (max 8 words), no numbering. "
            f'Respond as JSON: {{"tasks": ["...", "..."]}}'
        )
        try:
            raw = groq_client.complete(
                [{"role": "system", "content":
                  "You design short, practical learning task lists. Output JSON only."},
                 {"role": "user", "content": prompt}],
                temperature=0.5, max_tokens=500,
                response_format={"type": "json_object"},
            )
            titles = json.loads(raw).get("tasks", [])
        except Exception:
            logger.exception("learn plan generation failed")
            raise HTTPException(status_code=503,
                                detail="Couldn't build a plan just now. Please try again.")
        titles = [str(t).strip()[:255] for t in titles if str(t).strip()][:8]
        if not titles:
            raise HTTPException(status_code=503,
                                detail="Couldn't build a plan just now. Please try again.")
        for t in titles:
            db.add(Task(step_id=step.id, title=t))
        db.commit()
        db.refresh(step)
        tasks = step.tasks

    return LearnPlanReply(
        step_title=step.title, category=category, role=goal.role,
        tasks=[{"id": t.id, "title": t.title, "is_done": t.is_done} for t in tasks],
    )


@router.post("/turn", response_model=LearnTurnReply)
def teach_turn(req: LearnTurnRequest, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    row = _owned_step(db, current_user.id, req.step_id)
    if not row:
        raise HTTPException(status_code=404, detail="Step not found")
    step, path, goal = row
    category = _category(path.title)

    task = next((t for t in step.tasks if t.id == req.task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    all_tasks = ", ".join(t.title for t in step.tasks)
    common = (
        f"You are Ascend Coach, a friendly, encouraging tutor. The learner is "
        f"working toward becoming a {goal.role} and is learning the {category} "
        f"\"{step.title}\". The current task is \"{task.title}\". "
        f"For context, the full task list is: {all_tasks}. Teach ONLY the current "
        f"task, do not jump ahead to other tasks. Be concrete and practical, use a "
        f"real example, and keep it fairly short and readable. Never use em dashes; "
        f"use commas or periods. Plain language, no heavy formatting."
    )
    if req.mode == "guided":
        system = common + (
            " Style: a clear guided lesson. Explain the task with an example, then "
            "in one line invite the learner to ask a follow up or move on. Do not "
            "quiz them."
        )
    else:  # interactive
        system = common + (
            " Style: an interactive tutor. Give a brief explanation, then ask the "
            "learner ONE short question to check their understanding. If their last "
            "message answered your previous question, first tell them whether it was "
            "right and explain briefly, then continue."
        )

    messages = [{"role": "system", "content": system}]
    for m in req.messages[-10:]:
        messages.append({"role": m.role, "content": m.content[:4000]})
    if not req.messages:
        # First turn: kick off the lesson for this task.
        messages.append({"role": "user", "content":
                         f"Start teaching me the task: {task.title}"})

    try:
        reply = groq_client.complete(messages, temperature=0.5, max_tokens=900)
    except Exception:
        logger.exception("learn turn failed")
        raise HTTPException(status_code=503,
                            detail="I couldn't respond just now. Please try again.")
    return LearnTurnReply(reply=reply.strip())
