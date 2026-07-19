import json

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.catalog import CatalogItem, CatalogRole

CATEGORIES = ("skill", "course", "tool", "project")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _llm_suggestions(role_text: str) -> dict | None:
    """Generate suggestions for a role NOT in the catalog, via Groq. Returns a
    grouped dict of CatalogItemOut-shaped dicts, or None if unavailable."""
    if not settings.GROQ_API_KEYS or not role_text.strip():
        return None
    prompt = (
        f"Suggest a learning plan for someone whose goal/role is: \"{role_text}\". "
        "Return ONLY JSON with keys skills, courses, tools, projects.\n"
        "- skills: 5-7 items, each {name, description}\n"
        "- courses: 3-5 items, each {name, provider, estimated_hours, url}\n"
        "- tools: 3-6 items, each {name, description}\n"
        "- projects: 2-3 items, each {name, description, steps:[3-5 short strings]}\n"
        "Use real, well-known resources. Works for ANY field (tech or non-tech, "
        "e.g. UPSC, medicine, music). Keep names concise."
    )
    body = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
        "max_tokens": 1600,
    }
    try:
        resp = None
        for key in settings.GROQ_API_KEYS:  # rotate keys; use first that succeeds
            resp = httpx.post(GROQ_URL, json=body, timeout=45,
                              headers={"Authorization": f"Bearer {key}"})
            if resp.is_success:
                break
        resp.raise_for_status()
        data = json.loads(resp.json()["choices"][0]["message"]["content"])
    except Exception:
        return None

    grouped = {c: [] for c in CATEGORIES}
    nid = -1  # synthetic ids (not persisted; only used by the wizard UI)
    mapping = {"skill": "skills", "course": "courses", "tool": "tools", "project": "projects"}
    for cat, key in mapping.items():
        for it in (data.get(key) or [])[:8]:
            if not isinstance(it, dict) or not it.get("name"):
                continue
            grouped[cat].append({
                "id": nid,
                "category": cat,
                "name": str(it.get("name"))[:120],
                "description": it.get("description"),
                "provider": it.get("provider"),
                "url": it.get("url"),
                "estimated_hours": it.get("estimated_hours") if isinstance(it.get("estimated_hours"), int) else None,
                "steps": [str(s) for s in it.get("steps")] if isinstance(it.get("steps"), list) else None,
            })
            nid -= 1
    # Only return if we actually got something.
    return grouped if any(grouped[c] for c in CATEGORIES) else None


def list_roles(db: Session):
    return (
        db.query(CatalogRole)
        .filter(CatalogRole.slug != "general")
        .order_by(CatalogRole.name.asc())
        .all()
    )


def _match_role(db: Session, role_text: str) -> CatalogRole | None:
    """Fuzzy-match a free-text role to a catalog role."""
    if not role_text:
        return None
    q = role_text.strip().lower()
    roles = db.query(CatalogRole).filter(CatalogRole.slug != "general").all()

    # 1) exact name match
    for r in roles:
        if r.name.lower() == q:
            return r
    # 2) containment either direction
    for r in roles:
        rn = r.name.lower()
        if q in rn or rn in q:
            return r
    # 3) keyword overlap (any significant word in common)
    words = {w for w in q.replace("/", " ").split() if len(w) > 2}
    best, best_score = None, 0
    for r in roles:
        rwords = {w for w in r.name.lower().replace("/", " ").split() if len(w) > 2}
        score = len(words & rwords)
        if score > best_score:
            best, best_score = r, score
    return best if best_score > 0 else None


def _group(items) -> dict:
    grouped = {c: [] for c in CATEGORIES}
    for it in items:
        if it.category in grouped:
            grouped[it.category].append(it)
    return grouped


def get_suggestions(db: Session, role_text: str) -> dict:
    match = _match_role(db, role_text)
    if match:
        return {
            "matched": True,
            "label": match.name,
            "role": match,
            "items": _group(match.items),
        }

    # Not in the catalog → generate role-specific picks with the LLM (works for
    # any field, e.g. UPSC). Only when there's no catalog match — matched roles
    # always use the curated catalog above.
    llm = _llm_suggestions(role_text)
    if llm:
        return {"matched": True, "label": role_text or "your goal", "role": None, "items": llm}

    # last resort: the "general" role's items
    general = db.query(CatalogRole).filter(CatalogRole.slug == "general").first()
    return {
        "matched": False,
        "label": role_text or "your goal",
        "role": None,
        "items": _group(general.items) if general else _group([]),
    }
