"""Agentic AI coach — Groq tool-calling over the user's own SkillSync data.

The model can read (list goals/paths/steps/tasks) and act (add paths/steps/
tasks, mark things done). Every tool is scoped to the authenticated user, so
the coach can only ever touch that user's data.
"""
import json
import logging
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
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
from app.services import catalog_service

WRITE_TOOLS = {"create_goal", "create_path", "add_step", "create_task",
               "complete_task", "complete_step",
               "delete_goal", "delete_path", "delete_step", "delete_task"}

router = APIRouter()
logger = logging.getLogger("skillsync.chat")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_TOOL_ROUNDS = 8  # headroom for self-correction rounds; deadline still caps time

_rr = 0  # round-robin cursor across keys


def _ordered_keys():
    """Keys ordered round-robin so load spreads across them each call."""
    global _rr
    keys = settings.GROQ_API_KEYS
    if not keys:
        return []
    start = _rr % len(keys)
    _rr += 1
    return keys[start:] + keys[:start]


def _groq_call(payload: dict):
    """Call Groq, rotating keys; if all are rate-limited, wait and retry a few
    times (the client keeps showing its loader) before giving up."""
    resp = None
    for attempt in range(3):
        for key in _ordered_keys():
            resp = httpx.post(GROQ_URL, json=payload, timeout=30,
                              headers={"Authorization": f"Bearer {key}"})
            if resp.is_success:
                return resp
        if resp is not None and resp.status_code == 429 and attempt < 2:
            time.sleep(10)  # let the per-minute window recover, then retry
            continue
        break
    return resp

SYSTEM_PROMPT = (
    "You are Ascend Coach, the assistant inside Ascend — a learning-goal tracker "
    "(Goals → Learning paths → Steps → Tasks; users earn XP for completing things). "
    "You can BOTH answer questions and TAKE ACTIONS on the user's own data using the "
    "provided tools. Guidelines:\n"
    "- Only help with learning: skills, courses, study plans, roles, and using Ascend.\n"
    "- To act on something, first look it up (list_goals → list_paths → list_steps → "
    "list_tasks) to get the right id, then call the action tool. Tool id arguments must "
    "be REAL integers returned by those list tools — NEVER placeholders like "
    "'<path id>'; if you don't know an id yet, call the list tool first.\n"
    "- To START a new goal: you MUST know the target role first. If the user hasn't "
    "clearly stated it (e.g. they just said 'create a new goal'), ASK 'What role or "
    "subject do you want to focus on?' and WAIT for their answer — NEVER invent or "
    "assume a role. Once you have it, call create_goal (default 5 hrs/week, 12 weeks), "
    "then suggest_for_role. The suggestions appear as selectable chips the USER picks and "
    "adds via the UI — so after suggesting, do NOT add them yourself with tools. Just "
    "create the goal, suggest, and let them choose. Keep it conversational.\n"
    "- Use suggest_for_role ONLY when the user wants to ADD items to a specific goal "
    "(right after creating one, or when they ask to add more). For a plain 'what should I "
    "learn / give me suggestions for X' with NO active goal, do NOT call suggest_for_role — "
    "answer in prose with concrete, named skills, courses, and tools.\n"
    "- When the user says 'let's start with X', 'teach me X', or 'how do I learn X' about "
    "something already in their goal, they want GUIDANCE, not more items: give a short, "
    "ordered study plan in prose (learn A first, then B; practice with C). Do NOT call "
    "suggest_for_role for that.\n"
    "- Never mention chips, selecting, buttons, or any interface mechanics. When options "
    "will be shown, just say something like 'pick any of the options below to add them to "
    "your goal.'\n"
    "- Only call create_goal when the user EXPLICITLY asks to create/start a goal, or "
    "has just confirmed. 'I want to learn X' or 'help me with X' is INTEREST, not a "
    "create request: first ask something like 'Want me to create a new goal for X to "
    "track it, or just give you a study plan?' and WAIT for their answer. 'Get "
    "suggestions for X' or 'what should I learn for X' also means NO goal creation. "
    "Never create the same goal twice.\n"
    "- When options will be shown below your reply (after suggest_for_role with an "
    "active goal), do NOT list the items in your reply text too. Keep the reply to one "
    "short sentence inviting them to pick.\n"
    "- Deleting a goal or path is destructive (everything inside goes too). Before "
    "calling delete_goal or delete_path, CONFIRM once: say exactly what will be deleted "
    "(e.g. 'Delete the goal \"NLP\" and everything in it?') and WAIT for a yes. Skip the "
    "question only if the user already confirmed it in this conversation (e.g. their "
    "message says 'yes' or 'I confirm'). delete_step and delete_task may run directly.\n"
    "- To delete, use delete_goal/delete_path/delete_step/delete_task. CRITICAL: never "
    "claim you created, deleted, or completed anything unless the tool actually returned "
    "a success result in this turn. If a tool returns an error or you have no tool for "
    "the request, say so honestly — never pretend an action succeeded.\n"
    "- 'Add a skill/course/tool' (e.g. from a suggestion chip like 'Add \"Polity\"') = "
    "add a step to the matching learning path in an EXISTING goal. NEVER call create_goal "
    "for an 'Add' request. If it's unclear which goal (none or several match), ASK which "
    "goal — do not guess or create one. Create the path with create_path only if that "
    "category path is missing in the chosen goal.\n"
    "- After acting, tell the user in one short sentence what you did.\n"
    "- If a request is ambiguous (e.g. which goal), ask a brief clarifying question.\n"
    "- Be concise and practical. Plain text, minimal formatting. Never use em dashes "
    "(—) in replies; use commas or periods instead."
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
        "name": "create_goal",
        "description": "Create a new learning goal for a target role. Defaults: 5 hrs/week, 12 weeks unless the user specifies.",
        "parameters": {"type": "object", "properties": {
            "role": {"type": "string"},
            "hours_per_week": {"type": "integer"},
            "duration_weeks": {"type": "integer"}}, "required": ["role"]},
    }},
    {"type": "function", "function": {
        "name": "suggest_for_role",
        "description": "Get suggested skills, courses, tools and projects for a role (from the catalog, or AI-generated for custom roles like UPSC). Use to recommend what to add.",
        "parameters": {"type": "object", "properties": {
            "role": {"type": "string"}}, "required": ["role"]},
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
    {"type": "function", "function": {
        "name": "delete_goal",
        "description": "Delete a goal and everything under it.",
        "parameters": {"type": "object", "properties": {
            "goal_id": {"type": "integer"}}, "required": ["goal_id"]},
    }},
    {"type": "function", "function": {
        "name": "delete_path",
        "description": "Delete a learning path.",
        "parameters": {"type": "object", "properties": {
            "path_id": {"type": "integer"}}, "required": ["path_id"]},
    }},
    {"type": "function", "function": {
        "name": "delete_step",
        "description": "Delete a step.",
        "parameters": {"type": "object", "properties": {
            "step_id": {"type": "integer"}}, "required": ["step_id"]},
    }},
    {"type": "function", "function": {
        "name": "delete_task",
        "description": "Delete a task.",
        "parameters": {"type": "object", "properties": {
            "task_id": {"type": "integer"}}, "required": ["task_id"]},
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
    # The model sometimes passes ids as strings ("25") — coerce to int.
    for _k in ("goal_id", "path_id", "step_id", "task_id"):
        if _k in args and args[_k] is not None:
            try:
                args[_k] = int(args[_k])
            except (TypeError, ValueError):
                return {"error": f"invalid {_k}"}
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

        if name == "create_goal":
            role = str(args.get("role", "")).strip()
            if not role:
                return {"error": "role is required"}
            # Hard guard against duplicates: reuse an existing active goal with
            # the same role instead of creating a twin (prompt-only guards are
            # not reliable enough for this).
            existing = (db.query(Goal)
                        .filter(Goal.owner_id == uid,
                                Goal.is_deleted == False,  # noqa: E712
                                func.lower(Goal.role) == role.lower())
                        .first())
            if existing:
                return {"created_goal": {"id": existing.id, "role": existing.role},
                        "note": "a goal with this role already existed — reused it "
                                "instead of creating a duplicate"}
            g = Goal(owner_id=uid, role=role[:100],
                     hours_per_week=int(args.get("hours_per_week") or 5),
                     duration_weeks=int(args.get("duration_weeks") or 12))
            db.add(g); db.commit(); db.refresh(g)
            return {"created_goal": {"id": g.id, "role": g.role}}

        if name == "suggest_for_role":
            data = catalog_service.get_suggestions(db, str(args.get("role", "")))
            grouped = data.get("items", {}) or {}
            out = {}
            for cat in ("skill", "course", "tool", "project"):
                items = []
                for it in (grouped.get(cat, []) or [])[:6]:
                    d = it if isinstance(it, dict) else {
                        "name": getattr(it, "name", None),
                        "description": getattr(it, "description", None),
                        "provider": getattr(it, "provider", None),
                        "url": getattr(it, "url", None),
                        "estimated_hours": getattr(it, "estimated_hours", None),
                    }
                    if d.get("name"):
                        items.append({k: d.get(k) for k in
                                      ("name", "description", "provider", "url",
                                       "estimated_hours")})
                out[cat] = items
            return out

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

        if name == "delete_goal":
            g = _owned_goal(db, uid, args["goal_id"])
            if not g:
                return {"error": "goal not found"}
            g.is_deleted = True; db.commit()
            return {"deleted_goal": {"id": g.id, "role": g.role}}

        if name == "delete_path":
            p = _owned_path(db, uid, args["path_id"])
            if not p:
                return {"error": "path not found"}
            p.is_deleted = True; db.commit()
            return {"deleted_path": {"id": p.id}}

        if name == "delete_step":
            s = _owned_step(db, uid, args["step_id"])
            if not s:
                return {"error": "step not found"}
            db.delete(s); db.commit()
            return {"deleted_step": {"id": args["step_id"]}}

        if name == "delete_task":
            t = _owned_task(db, uid, args["task_id"])
            if not t:
                return {"error": "task not found"}
            db.delete(t); db.commit()
            return {"deleted_task": {"id": args["task_id"]}}

        return {"error": f"unknown tool {name}"}
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/chat", response_model=ChatReply)
def chat(payload: ChatRequest, db: Session = Depends(get_db),
         current_user: User = Depends(get_current_user)):
    if not settings.GROQ_API_KEYS:
        raise HTTPException(status_code=503, detail="The AI coach isn't configured yet.")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if payload.goal_id:
        messages.append({"role": "system", "content":
            f"Context: the user is currently working on goal id {payload.goal_id}. "
            "For add/create/complete/list requests that don't name a goal, use THIS goal "
            "by default (don't ask which goal). Only ask if no goal id is given here."})
    messages += [{"role": m.role, "content": m.content} for m in payload.messages][-12:]

    changed = False
    suggestions: list = []
    active_goal_id = None  # goal the user is building, so the UI can add to it
    # Stay well under gunicorn's 120s so we always answer gracefully rather
    # than letting the worker get killed mid-request (raw 502 to the user).
    deadline = time.monotonic() + 90
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            if time.monotonic() > deadline:
                return {"reply": "That took longer than expected. Part of it may be "
                                 "done. Check your goal and tell me what's missing.",
                        "changed": changed,
                        "suggestions": suggestions if (active_goal_id or payload.goal_id) else [],
                        "goal_id": active_goal_id or payload.goal_id}
            payload_json = {
                "model": settings.GROQ_MODEL,
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.2,
                "max_tokens": 900,
            }
            resp = _groq_call(payload_json)
            if not resp.is_success:
                logger.error("groq %s: %s", resp.status_code, resp.text[:500])
                # The model sometimes emits an invalid tool call (e.g. a
                # placeholder string where an integer id belongs). Groq rejects
                # the whole request with 400/tool_use_failed — feed the error
                # back so the model looks up real ids and retries.
                if resp.status_code == 400:
                    try:
                        err = resp.json().get("error", {})
                    except Exception:
                        err = {}
                    if err.get("code") == "tool_use_failed":
                        messages.append({"role": "system", "content":
                            "Correction: your previous tool call was invalid — "
                            + str(err.get("message", ""))[:300]
                            + ". Tool arguments must be REAL integer ids. Call "
                            "list_goals/list_paths/list_steps first to get the "
                            "actual id, then retry the tool with that id."})
                        continue
                if resp.status_code == 429:
                    return {"reply": "Sorry, I couldn't respond just now. Please try "
                                     "again in a moment.",
                            "changed": changed,
                        "suggestions": suggestions if (active_goal_id or payload.goal_id) else [],
                        "goal_id": active_goal_id or payload.goal_id}
                resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                target = active_goal_id or payload.goal_id
                reply_text = (msg.get("content") or "").strip()
                # No goal to add to → no chips, so spell out the suggestions in text.
                if not target and suggestions:
                    by: dict = {}
                    for s in suggestions:
                        by.setdefault(s["category"], []).append(s["name"])
                    lines = [f"{c.capitalize()}s: " + ", ".join(by[c])
                             for c in ("skill", "course", "tool", "project") if by.get(c)]
                    if lines:
                        reply_text = (reply_text + "\n\n" + "\n".join(lines)).strip()
                return {"reply": reply_text, "changed": changed,
                        "suggestions": suggestions if target else [],
                        "goal_id": target}

            messages.append({"role": "assistant", "content": msg.get("content") or "",
                             "tool_calls": tool_calls})
            for tc in tool_calls:
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                fname = tc["function"]["name"]
                result = run_tool(fname, args, db, current_user.id)
                # Only flag a data change when the write actually succeeded.
                if fname in WRITE_TOOLS and isinstance(result, dict) and "error" not in result:
                    changed = True
                # Surface suggestions as selectable chips in the chat.
                if fname == "suggest_for_role" and isinstance(result, dict):
                    suggestions = [{"category": cat, **it}
                                   for cat in ("skill", "course", "tool", "project")
                                   for it in (result.get(cat) or [])
                                   if isinstance(it, dict) and it.get("name")]
                # Remember the goal being built so the UI can add chips to it.
                if fname == "create_goal" and isinstance(result, dict) and result.get("created_goal"):
                    active_goal_id = result["created_goal"]["id"]
                messages.append({"role": "tool", "tool_call_id": tc["id"],
                                 "content": json.dumps(result)})
        return {"reply": "I couldn't finish that. Try rephrasing or breaking it into steps.",
                "changed": changed,
                        "suggestions": suggestions if (active_goal_id or payload.goal_id) else [],
                        "goal_id": active_goal_id or payload.goal_id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("chat agent failed")
        raise HTTPException(status_code=502, detail="The coach is unavailable right now. Try again.")
