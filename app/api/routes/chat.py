"""AI coach endpoint — proxies to Groq's free hosted LLM API.

Auth-required so the API key isn't abused. Scoped by a system prompt to only
help with learning topics.
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatReply, ChatRequest

router = APIRouter()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are Ascend Coach, the assistant inside Ascend — a learning-goal "
    "tracker. Only help with learning: skills to build, courses and study "
    "resources, learning plans, career roles, and using Ascend itself "
    "(goals, learning paths, steps, tasks, XP, streaks). If asked anything "
    "unrelated, briefly and politely decline and steer back to learning. "
    "Be concise, friendly, and practical — prefer concrete next steps and name "
    "real, well-known courses or resources when useful."
)


@router.post("/chat", response_model=ChatReply)
def chat(payload: ChatRequest, current_user: User = Depends(get_current_user)):
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=503, detail="The AI coach isn't configured yet."
        )
    # Bound context: keep the last 12 turns.
    history = [{"role": m.role, "content": m.content} for m in payload.messages][-12:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history]
    try:
        resp = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": settings.GROQ_MODEL,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 700,
            },
            timeout=30,
        )
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"].strip()
        return {"reply": reply}
    except Exception:
        raise HTTPException(
            status_code=502, detail="The coach is unavailable right now. Try again."
        )
