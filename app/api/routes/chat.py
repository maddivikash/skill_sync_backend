"""Agentic AI coach — Groq tool-calling over the user's own SkillSync data.

The model can read (list goals/paths/steps/tasks) and act (add paths/steps/
tasks, mark things done). Every tool is scoped to the authenticated user, so
the coach can only ever touch that user's data.
"""
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.goal import Goal
from app.models.learning_path import LearningPath
from app.models.step import Step
from app.models.task import Task
from app.models.user import User
from app.schemas.chat import ChatReply, ChatRequest

router = APIRouter()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = (
    "You are Ascend Coach, the assistant inside Ascend — a learning-goal tracker "
    "(Goals → Learning paths → Steps → Tasks; users earn XP for completing things). "
    "You can BOTH answer questions and TAKE ACTIONS on the user's own data using the "
    "provided tools. Guidelines:\n"
    "- Only help with learning: skills, courses, study plans, roles, and using Ascend.\n"
    "- To act on something, first look it up (list_goals → list_paths → list_steps → "
    "list_tasks) to get the right id, then call the action tool.\n"
    "- 'Add a skill/course/tool' = add a step to the matching learning path (Skills/"
    "Courses/Tools). If that path doesn't exist, create it with create_path first.\n"
    "- After acting, tell the user in one short sentence what you did.\n"
    "- If a request is ambiguous (e.g. which goal), ask a brief clarifying question.\n"
    "- Be concise and practical. Plain text, minimal formatting."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "list_goals",
        "description": "List the user's learning goals (id, role, active).",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "list_paths",
        "description": "List the learning paths in a goal.",
        "parameters": {"type": "object", "properties": {
            "goal_id": {"type": "integer"}}, "required": ["goal_id"]},
    }},
    {"type": "function", "function": {
        "name": "list_steps",
        "description": "List the steps in a learning path (e.g. the skills/courses/tools under it).",
        "parameters": {"type": "object", "properties": {
            "path_id": {"type": "integer"}}, "required": ["path_id"]},
    }},
    {"type": "function", "function": {
        "name": "list_tasks",
        "description": "List the tasks under a step.",
        "parameters": {"type": "object", "properties": {
            "step_id": {"type": "integer"}}, "required": ["step_id"]},
    }},
    {"type": "function", "function": {
        "name": "create_path",
        "description": "Create a new learning path in a goal (e.g. Skills, Courses, Tools).",
        "parameters": {"type": "object", "properties": {
            "goal_id": {"type": "integer"}, "title": {"type": "string"}},
            "required": ["goal_id", "title"]},
    }},
    {"type": "function", "function": {
        "name": "add_step",
        "description": "Add a step to a path (use this to add a skill, course, or tool).",
        "parameters": {"type": "object", "properties": {
            "path_id": {"type": "integer"}, "title": {"type": "string"}},
            "required": ["path_id", "title"]},
    }},
    {"type": "function", "function": {
        "name": "create_task",
        "description": "Add a task under a step.",
        "parameters": {"type": "object", "properties": {
            "step_id": {"type": "integer"}, "title": {"type": "string"}},
            "required": ["step_id", "title"]},
    }},
    {"type": "function", "function": {
        "name": "complete_task",
        "description": "Mark a task as done.",
        "parameters": {"type": "object", "properties": {
            "task_id": {"type": "integer"}}, "required": ["task_id"]},
    }},
    {"type": "function", "function": {
        "name": "complete_step",
        "description": "Mark a step as done.",
        "parameters": {"type": "object", "properties": {
            "step_id": {"type": "integer"}}, "required": ["step_id"]},
    }},
]


# ---- ownership-scoped lookups ----
def _owned_goal(db, uid, gid):
    return db.query(Goal).filter(Goal.id == gid, Goal.owner_id == uid,
                                 Goal.is_deleted == False).first()  # noqa: E712


def _owned_path(db, uid, pid):
    return (db.query(LearningPath).join(Goal, LearningPath.goal_id == Goal.id)
            .filter(LearningPath.id == pid, Goal.owner_id == uid,
                    LearningPath.is_deleted == False).first())  # noqa: E712


def _owned_step(db, uid, sid):
    return (db.query(Step).join(LearningPath, Step.path_id == LearningPath.id)
            .join(Goal, LearningPath.goal_id == Goal.id)
            .filter(Step.id == sid, Goal.owner_id == uid).first())


def _owned_task(db, uid, tid):
    return (db.query(Task).join(Step, Task.step_id == Step.id)
            .join(LearningPath, Step.path_id == LearningPath.id)
            .join(Goal, LearningPath.goal_id == Goal.id)
            .filter(Task.id == tid, Goal.owner_id == uid).first())


def run_tool(name: str, args: dict, db: Session, uid: int) -> dict:
    try:
        if name == "list_goals":
            gs = db.query(Goal).filter(Goal.owner_id == uid,
                                       Goal.is_deleted == False).all()  # noqa: E712
            return {"goals": [{"id": g.id, "role": g.role, "active": g.is_active} for g in gs]}

        if name == "list_paths":
            g = _owned_goal(db, uid, args["goal_id"])
            if not g:
                return {"error": "goal not found"}
            return {"paths": [{"id": p.id, "title": p.title}
                              for p in g.learning_paths if not p.is_deleted]}

        if name == "list_steps":
            p = _owned_path(db, uid, args["path_id"])
            if not p:
                return {"error": "path not found"}
            return {"steps": [{"id": s.id, "title": s.title, "done": s.is_done} for s in p.steps]}

        if name == "list_tasks":
            s = _owned_step(db, uid, args["step_id"])
            if not s:
                return {"error": "step not found"}
            return {"tasks": [{"id": t.id, "title": t.title, "done": t.is_done} for t in s.tasks]}

        if name == "create_path":
            if not _owned_goal(db, uid, args["goal_id"]):
                return {"error": "goal not found"}
            p = LearningPath(goal_id=args["goal_id"], title=args["title"][:255])
            db.add(p); db.commit(); db.refresh(p)
            return {"created_path": {"id": p.id, "title": p.title}}

        if name == "add_step":
            if not _owned_path(db, uid, args["path_id"]):
                return {"error": "path not found"}
            s = Step(path_id=args["path_id"], title=args["title"][:255])
            db.add(s); db.commit(); db.refresh(s)
            return {"added_step": {"id": s.id, "title": s.title}}

        if name == "create_task":
            if not _owned_step(db, uid, args["step_id"]):
                return {"error": "step not found"}
            t = Task(step_id=args["step_id"], title=args["title"][:255])
            db.add(t); db.commit(); db.refresh(t)
            return {"created_task": {"id": t.id, "title": t.title}}

        if name == "complete_task":
            t = _owned_task(db, uid, args["task_id"])
            if not t:
                return {"error": "task not found"}
            t.is_done = True; db.commit()
            return {"completed_task": {"id": t.id, "title": t.title}}

        if name == "complete_step":
            s = _owned_step(db, uid, args["step_id"])
            if not s:
                return {"error": "step not found"}
            s.is_done = True; db.commit()
            return {"completed_step": {"id": s.id, "title": s.title}}

        return {"error": f"unknown tool {name}"}
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/chat", response_model=ChatReply)
def chat(payload: ChatRequest, db: Session = Depends(get_db),
         current_user: User = Depends(get_current_user)):
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="The AI coach isn't configured yet.")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in payload.messages][-12:]

    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            resp = httpx.post(GROQ_URL, headers=headers, timeout=45, json={
                "model": settings.GROQ_MODEL,
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.2,
                "max_tokens": 900,
            })
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                return {"reply": (msg.get("content") or "").strip()}

            messages.append({"role": "assistant", "content": msg.get("content") or "",
                             "tool_calls": tool_calls})
            for tc in tool_calls:
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = run_tool(tc["function"]["name"], args, db, current_user.id)
                messages.append({"role": "tool", "tool_call_id": tc["id"],
                                 "content": json.dumps(result)})
        return {"reply": "I couldn't finish that — try rephrasing or breaking it into steps."}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="The coach is unavailable right now. Try again.")
