"""Daily 'What's new in AI' digest: fetch RSS feeds, summarize with Groq, save a Post.

Run inside the api container (host cron calls this once a day):
    python -m app.services.digest_service            # creates a DRAFT
    python -m app.services.digest_service --publish  # creates and publishes

Zero extra dependencies: RSS parsed with the stdlib, summary via the shared
Groq client. Drafts are reviewed/published from the app by an admin user.
"""
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime

import httpx
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.post import Post
from app.services.groq_client import complete

logger = logging.getLogger("skillsync.digest")

# Official/first-party feeds first, then good aggregators. All free, no keys.
FEEDS = [
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
    ("MIT Technology Review", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("Hacker News AI", "https://hnrss.org/newest?q=AI+OR+LLM&points=100"),
]
MAX_AGE_HOURS = 36
MAX_CANDIDATES = 40


def _text(el, *names):
    for n in names:
        found = el.find(n)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
    return ""


def _parse_date(raw: str):
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).replace(tzinfo=None)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def fetch_candidates(hours: int = MAX_AGE_HOURS) -> list[dict]:
    """Recent items across all feeds: [{source, title, url, snippet, published}]."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    out, seen = [], set()
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for source, url in FEEDS:
        try:
            r = httpx.get(url, timeout=15, follow_redirects=True,
                          headers={"User-Agent": "AscendDigest/1.0 (+https://ascenddaily.in)"})
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception as e:
            logger.warning("feed %s failed: %s", source, e)
            continue
        entries = root.findall(".//item") or root.findall(".//atom:entry", ns)
        for e in entries:
            title = _text(e, "title", "{http://www.w3.org/2005/Atom}title")
            link = _text(e, "link")
            if not link:
                a = e.find("{http://www.w3.org/2005/Atom}link")
                link = a.get("href") if a is not None else ""
            pub = _parse_date(_text(e, "pubDate", "{http://www.w3.org/2005/Atom}published",
                                    "{http://www.w3.org/2005/Atom}updated"))
            if not title or not link or (pub and pub < cutoff):
                continue
            key = title.lower()[:80]
            if key in seen:
                continue
            seen.add(key)
            snippet = _strip_html(_text(e, "description",
                                        "{http://www.w3.org/2005/Atom}summary",
                                        "{http://www.w3.org/2005/Atom}content"))[:400]
            out.append({"source": source, "title": title, "url": link,
                        "snippet": snippet, "published": pub.isoformat() if pub else None})
    out.sort(key=lambda x: x["published"] or "", reverse=True)
    return out[:MAX_CANDIDATES]


SYSTEM_PROMPT = """You write a short daily digest called "What's new in AI" for Ascend, a learning
tracker that turns a target role into a plan. Readers are working professionals and students
who want to stay current and know what to learn next.

Rules:
- Pick the 5 most important stories from the candidates. Prefer launches, research, and
  policy over opinion pieces. Skip duplicates of the same news.
- Plain, direct language. No hype words, no exclamation marks, no em dashes.
- Each summary is 1 to 2 sentences of fact. why_it_matters is 1 sentence for a learner.
- learn_next: 2 sentences telling the reader one concrete skill or topic to study this week
  based on today's stories, and why.
- learn_role: the single Ascend target role most relevant to learn_next, e.g.
  "AI Engineer", "Machine Learning Engineer", "Data Scientist", "Backend Developer",
  "Product Manager", "DevOps Engineer".
- Only use the source_url values given. Never invent a URL or a fact not in the candidates.

Return ONLY JSON with this shape:
{"title": str, "summary": str,
 "items": [{"headline": str, "summary": str, "why_it_matters": str,
            "source_name": str, "source_url": str}],
 "learn_next": str, "learn_role": str}"""


def summarize(candidates: list[dict], day: date) -> dict:
    user = json.dumps({"date": day.isoformat(), "candidates": candidates}, ensure_ascii=False)
    raw = complete(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": user}],
        temperature=0.3, max_tokens=2500,
        response_format={"type": "json_object"},
    )
    data = json.loads(raw)
    allowed = {c["url"] for c in candidates}
    data["items"] = [i for i in data.get("items", []) if i.get("source_url") in allowed][:6]
    if not data["items"]:
        raise RuntimeError("digest produced no items with valid sources")
    return data


def _clean(text):
    """House style: no em/en dashes, plain apostrophes and hyphens."""
    if not isinstance(text, str):
        return text
    return (text.replace(" — ", ": ").replace(" – ", ": ").replace("—", ", ").replace("–", "-")
                .replace("\u2011", "-").replace("\u2019", "'").replace("\u2018", "'")
                .replace("\u201c", '"').replace("\u201d", '"'))


def _clean_data(data: dict) -> dict:
    for k in ("title", "summary", "learn_next", "learn_role"):
        data[k] = _clean(data.get(k))
    for it in data.get("items", []):
        for k in ("headline", "summary", "why_it_matters", "source_name"):
            it[k] = _clean(it.get(k))
    return data


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:120]


def create_digest(db: Session, day: date | None = None, publish: bool = False) -> Post:
    day = day or date.today()
    base_slug = f"whats-new-in-ai-{day.isoformat()}"
    existing = db.query(Post).filter(Post.slug == base_slug).first()
    if existing:
        logger.info("digest for %s already exists (id=%s)", day, existing.id)
        return existing

    candidates = fetch_candidates()
    if len(candidates) < 3:
        raise RuntimeError(f"only {len(candidates)} candidate stories; not enough for a digest")
    data = _clean_data(summarize(candidates, day))

    post = Post(
        slug=base_slug,
        title=f"What's new in AI: {day.strftime('%d %b %Y')}",
        summary=data.get("summary") or "",
        items_json=json.dumps(data["items"], ensure_ascii=False),
        learn_next=data.get("learn_next"),
        learn_role=(data.get("learn_role") or None),
        status="published" if publish else "draft",
        published_at=datetime.utcnow() if publish else None,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    logger.info("digest %s created id=%s status=%s items=%d",
                day, post.id, post.status, len(data["items"]))
    return post


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    publish = "--publish" in sys.argv
    with SessionLocal() as db:
        p = create_digest(db, publish=publish)
        print(f"post id={p.id} slug={p.slug} status={p.status}")
