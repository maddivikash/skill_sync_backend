from sqlalchemy.orm import Session

from app.models.catalog import CatalogItem, CatalogRole

CATEGORIES = ("skill", "course", "tool", "project")


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

    # fall back to the "general" role's items
    general = db.query(CatalogRole).filter(CatalogRole.slug == "general").first()
    return {
        "matched": False,
        "label": role_text or "your goal",
        "role": None,
        "items": _group(general.items) if general else _group([]),
    }
