"""JSON API for the daily AI digest.

Public:  GET /posts/            published list (used by landing page + dashboard widget)
         GET /posts/{slug}      one published post
Admin:   POST /posts/generate   build today's digest (draft by default)
         PATCH /posts/{id}      publish / unpublish / edit
         GET /posts/admin/all   every post incl. drafts
Admin = logged-in user whose email is in ADMIN_EMAILS.
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.post import Post
from app.models.user import User
from app.services.digest_service import create_digest

router = APIRouter(prefix="/posts", tags=["Posts"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if (current_user.email or "").lower() not in settings.ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user


def serialize(p: Post, full: bool = True) -> dict:
    d = {
        "id": p.id, "slug": p.slug, "title": p.title, "summary": p.summary,
        "learn_next": p.learn_next, "learn_role": p.learn_role, "status": p.status,
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
    if full:
        d["items"] = json.loads(p.items_json or "[]")
    return d


@router.get("/")
def list_posts(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    rows = (db.query(Post).filter(Post.status == "published")
            .order_by(Post.published_at.desc()).limit(limit).all())
    return [serialize(p, full=False) for p in rows]


@router.get("/admin/all")
def list_all(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.query(Post).order_by(Post.created_at.desc()).limit(100).all()
    return [serialize(p, full=False) for p in rows]


@router.get("/{slug}")
def get_post(slug: str, db: Session = Depends(get_db)):
    p = db.query(Post).filter(Post.slug == slug, Post.status == "published").first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    return serialize(p)


@router.post("/generate", status_code=201)
def generate(publish: bool = False, db: Session = Depends(get_db),
             _: User = Depends(require_admin)):
    try:
        p = create_digest(db, publish=publish)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return serialize(p)


class PostPatch(BaseModel):
    status: Optional[str] = None      # "draft" | "published"
    title: Optional[str] = None
    summary: Optional[str] = None
    learn_next: Optional[str] = None
    learn_role: Optional[str] = None


@router.patch("/{post_id}")
def patch_post(post_id: int, body: PostPatch, db: Session = Depends(get_db),
               _: User = Depends(require_admin)):
    p = db.get(Post, post_id)
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    if body.status is not None:
        if body.status not in ("draft", "published"):
            raise HTTPException(status_code=422, detail="status must be draft or published")
        p.status = body.status
        if body.status == "published" and not p.published_at:
            p.published_at = datetime.utcnow()
    for f in ("title", "summary", "learn_next", "learn_role"):
        v = getattr(body, f)
        if v is not None:
            setattr(p, f, v)
    db.commit()
    db.refresh(p)
    return serialize(p)
