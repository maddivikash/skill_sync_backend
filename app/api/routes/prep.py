"""Job prep: paste a job description, get a readiness score, a gap analysis,
and a deadline-dated prep plan created as a real goal.

This is the "prepare for THIS job" flow: the LLM compares the JD against what
the user has already built in Ascend (their existing steps), estimates
readiness, and produces a plan whose tasks carry due dates spread over the
chosen number of days.
"""
import io
import json
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.goal import Goal
from app.models.learning_path import LearningPath
from app.models.step import Step
from app.models.task import Task
from app.models.user import User
from app.schemas.prep import PrepReply, PrepRequest
from app.services import groq_client

router = APIRouter(prefix="/prep", tags=["Job prep"])
logger = logging.getLogger("skillsync.prep")


def _skill_inventory(db: Session, uid: int) -> list:
    """Titles of everything the user has in their goals (their current skills)."""
    rows = (db.query(Step.title)
            .join(LearningPath, Step.path_id == LearningPath.id)
            .join(Goal, LearningPath.goal_id == Goal.id)
            .filter(Goal.owner_id == uid, Goal.is_deleted.is_(False))
            .limit(120).all())
    return sorted({r[0] for r in rows})


MAX_UPLOAD = 5 * 1024 * 1024  # 5 MB


@router.post("/extract")
async def extract_jd(file: UploadFile = File(...),
                     current_user: User = Depends(get_current_user)):
    """Pull the text out of an uploaded JD file (PDF or plain text)."""
    name = (file.filename or "").lower()
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="File is too large (max 5 MB).")

    text = ""
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            logger.exception("pdf extraction failed")
            raise HTTPException(status_code=422,
                                detail="Couldn't read that PDF. Try pasting the text instead.")
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=415,
                            detail="Use a PDF or text file, or paste the description.")

    text = text.strip()
    if len(text) < 40:
        raise HTTPException(status_code=422,
                            detail="Couldn't find enough text in that file. Try pasting it.")
    return {"text": text[:15000]}


ANALYZE_SYSTEM = (
    "You are a career-prep planner. You compare a job description against a "
    "candidate's current skills and produce a realistic prep plan. Output "
    "JSON only, no prose."
)


@router.post("/analyze", response_model=PrepReply)
def analyze(req: PrepRequest, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    inventory = _skill_inventory(db, current_user.id)
    jd = req.jd_text.strip()[:8000]

    prompt = (
        f"JOB DESCRIPTION:\n{jd}\n\n"
        f"CANDIDATE'S CURRENT SKILLS (from their learning tracker): "
        f"{inventory if inventory else '(none listed)'}\n\n"
        f"The candidate has {req.days} days to prepare. Analyze and respond as JSON:\n"
        "{\n"
        '  "role": "<the job title, short>",\n'
        '  "summary": "<what this job really needs, 2 sentences>",\n'
        '  "readiness": <0-100 integer, honest estimate of how ready they are NOW>,\n'
        '  "strengths": ["<requirement they already cover>", ...],\n'
        '  "gaps": ["<missing/weak requirement>", ...],\n'
        '  "plan": [\n'
        '    {"path": "<area, e.g. Core skills>", "steps": [\n'
        '      {"title": "<skill/topic>", "description": "<one line why it matters for THIS jd>",\n'
        '       "tasks": [{"title": "<concrete action>", "day": <1..%d>}]}\n'
        "    ]}\n"
        "  ]\n"
        "}\n"
        "Rules: 2 to 4 paths; 2 to 4 steps per path; 1 to 3 tasks per step; task "
        "days spread realistically across the %d days (earlier = foundational). "
        "Plan ONLY the gaps, do not re-teach strengths. Keep titles under 8 words. "
        "No em dashes anywhere." % (req.days, req.days)
    )

    try:
        raw = groq_client.complete(
            [{"role": "system", "content": ANALYZE_SYSTEM},
             {"role": "user", "content": prompt}],
            temperature=0.4, max_tokens=2800,
            response_format={"type": "json_object"},
        )
        data = json.loads(raw)
    except Exception:
        logger.exception("prep analyze failed")
        raise HTTPException(status_code=503,
                            detail="Couldn't analyze that just now. Please try again.")

    role = str(data.get("role") or "Target role").strip()[:90]
    readiness = max(0, min(100, int(data.get("readiness") or 0)))
    plan = data.get("plan") or []
    if not plan:
        raise HTTPException(status_code=503,
                            detail="Couldn't build a plan from that description.")

    # Create the goal + dated plan.
    weeks = max(1, round(req.days / 7))
    goal = Goal(owner_id=current_user.id, role=role, hours_per_week=8,
                duration_weeks=weeks, jd_text=jd, readiness_base=readiness)
    db.add(goal)
    db.flush()

    today = date.today()
    total_tasks = 0
    for p in plan[:4]:
        path = LearningPath(goal_id=goal.id,
                            title=str(p.get("path") or "Plan").strip()[:120])
        db.add(path)
        db.flush()
        for order, s in enumerate((p.get("steps") or [])[:4], start=1):
            title = str(s.get("title") or "").strip()[:255]
            if not title:
                continue
            step = Step(path_id=path.id, title=title,
                        description=(str(s.get("description") or "").strip()[:900] or None),
                        step_order=order)
            db.add(step)
            db.flush()
            for t in (s.get("tasks") or [])[:3]:
                t_title = str(t.get("title") or "").strip()[:255]
                if not t_title:
                    continue
                try:
                    day = max(1, min(req.days, int(t.get("day") or 1)))
                except (TypeError, ValueError):
                    day = 1
                db.add(Task(step_id=step.id, title=t_title,
                            due_date=today + timedelta(days=day)))
                total_tasks += 1
    db.commit()

    return PrepReply(
        goal_id=goal.id, role=role,
        summary=str(data.get("summary") or "").strip()[:500],
        readiness=readiness,
        strengths=[str(x).strip()[:120] for x in (data.get("strengths") or [])[:8]],
        gaps=[str(x).strip()[:120] for x in (data.get("gaps") or [])[:8]],
        total_tasks=total_tasks,
    )
