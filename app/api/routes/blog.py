"""Server-rendered public pages: /blog, /blog/{slug}, /robots.txt, /sitemap.xml.

Why server-side: the app is a Vite SPA, which search engines and link previews
(LinkedIn, WhatsApp, Slack) see as an empty <div id="root">. Caddy routes these
paths to the API so crawlers get real HTML with title/description/OG tags.
Plain f-strings + html.escape: no template engine dependency.
"""
import json
from html import escape as h

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.deps import get_db
from app.models.post import Post

router = APIRouter(tags=["Public site"])

CSS = """
:root{--bg:#f4efe4;--surface:#fff;--surface-2:#faf5ec;--border:#e7dece;--text:#29211a;--muted:#6f6357;--soft:#a2978a;--brand:#a8492f;--brand-dark:#8f3c26;--brand-soft:#f3e5da}
@media(prefers-color-scheme:dark){:root{--bg:#1b1510;--surface:#241c15;--surface-2:#2d241b;--border:#392e23;--text:#f1e9dd;--muted:#bcae9d;--soft:#8c7f6f;--brand:#d5805f;--brand-dark:#c56f4e;--brand-soft:#2f2016}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 "Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
a{color:var(--brand)}.wrap{max-width:780px;margin:0 auto;padding:28px 22px 72px}
header.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:44px}
.brand{display:flex;align-items:center;gap:10px;font-family:"Fraunces",Georgia,serif;font-weight:700;font-size:24px;text-decoration:none;color:var(--text)}
.brand b{color:var(--brand);font-weight:700}.brand .mark{width:30px;height:30px;border-radius:9px;background:var(--brand);display:inline-flex;align-items:center;justify-content:center}
nav{display:flex;align-items:center;gap:18px}nav a{text-decoration:none;color:var(--muted);font-weight:600;font-size:15px}
.btn{display:inline-block;background:var(--brand);color:#fff!important;text-decoration:none;padding:10px 20px;border-radius:999px;font-weight:600}.btn:hover{background:var(--brand-dark)}
.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:12px;color:var(--brand);font-weight:700}
h1{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:clamp(34px,5vw,48px);line-height:1.1;margin:10px 0 14px;letter-spacing:-.01em}
h1 em{font-style:italic;color:var(--brand)}
h2{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:22px;line-height:1.25;margin:0 0 8px}
.lede{color:var(--muted);font-size:18px}.meta{color:var(--soft);font-size:14px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:22px 24px;margin:18px 0;box-shadow:0 1px 2px rgba(60,42,28,.06)}
.card p{margin:6px 0}.why{color:var(--muted)}.why::before{content:"Why it matters: ";color:var(--brand);font-weight:600}.src{font-size:14px;color:var(--soft)}
.list a.title{font-family:"Fraunces",Georgia,serif;font-size:24px;font-weight:600;text-decoration:none;color:var(--text);line-height:1.25}
.list a.title:hover{color:var(--brand)}
.cta{background:var(--brand-soft);border:1px solid var(--border);border-radius:18px;padding:26px;margin-top:36px}
.cta h3{font-family:"Fraunces",Georgia,serif;font-size:24px;margin:6px 0 10px}
.weekly{margin-top:56px;padding-top:36px;border-top:1px solid var(--border)}
h2.section{font-size:clamp(28px,4vw,38px);margin:8px 0 10px}h2.section em{font-style:italic;color:var(--brand)}
footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--border);color:var(--soft);font-size:14px}
@media(max-width:560px){nav a:not(.btn){display:none}}
"""


def _page(title: str, description: str, body: str, canonical: str, og_type="website") -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{h(title)}</title>
<meta name="description" content="{h(description)}">
<link rel="canonical" href="{h(canonical)}">
<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="Ascend">
<meta property="og:title" content="{h(title)}"><meta property="og:description" content="{h(description)}">
<meta property="og:url" content="{h(canonical)}"><meta name="twitter:card" content="summary">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,600;0,700;1,500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">
<header class="top"><a class="brand" href="/"><span class="mark"><svg viewBox="0 0 24 24" width="18" height="18" fill="none"><path d="M4 13l4 4L20 5" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span>As<b>cend</b></span></a>
<nav><a href="/blog">All digests</a><a href="/login">Sign in</a><a class="btn" href="/register">Start free</a></nav></header>
{body}
<footer>Ascend turns a target role into a plan you can finish. <a href="/register">Create your plan</a> · <a href="/login">Sign in</a></footer>
</div></body></html>"""


def _cta(post: Post) -> str:
    role = post.learn_role or "AI Engineer"
    learn = f"<p>{h(post.learn_next)}</p>" if post.learn_next else ""
    return f"""<section class="cta"><span class="eyebrow">What to learn from this</span>
<h3>Turn today's news into a plan</h3>{learn}
<a class="btn" href="/register?role={h(role)}">Build my {h(role)} plan</a></section>"""


@router.get("/blog", response_class=HTMLResponse)
def blog_index(db: Session = Depends(get_db)):
    def _cards(kind, limit, empty):
        rows = (db.query(Post).filter(Post.status == "published", Post.kind == kind)
                .order_by(Post.published_at.desc()).limit(limit).all())
        return "".join(
            f"""<article class="card list"><a class="title" href="/blog/{h(p.slug)}">{h(p.title)}</a>
<p class="meta">{p.published_at.strftime('%d %b %Y') if p.published_at else ''}</p>
<p>{h(p.summary)}</p></article>""" for p in rows
        ) or f"<p class='lede'>{empty}</p>"
    body = f"""<span class="eyebrow">Daily digest</span><h1>What's new <em>in AI.</em></h1>
<p class="lede">Five stories a day, one thing to learn from them. Written for people building a career, not chasing hype.</p>
{_cards("daily", 14, "First digest lands soon.")}
<section class="weekly"><span class="eyebrow">Weekly highlights</span>
<h2 class="section">The week, <em>in one read.</em></h2>
<p class="lede">Every Sunday: the stories from the past seven days worth remembering, and the one theme behind them.</p>
{_cards("weekly", 8, "First weekly roundup lands this Sunday.")}</section>"""
    return _page("What's new in AI | Ascend",
                 "A daily five-story AI digest with one concrete thing to learn next.",
                 body, f"{settings.SITE_URL}/blog")


@router.get("/blog/{slug}", response_class=HTMLResponse)
def blog_post(slug: str, db: Session = Depends(get_db)):
    p = db.query(Post).filter(Post.slug == slug, Post.status == "published").first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    items = json.loads(p.items_json or "[]")
    stories = "".join(
        f"""<article class="card"><h2>{h(i.get('headline',''))}</h2>
<p>{h(i.get('summary',''))}</p><p class="why">{h(i.get('why_it_matters',''))}</p>
<p class="src">Source: <a href="{h(i.get('source_url','#'))}" rel="noopener nofollow" target="_blank">{h(i.get('source_name','link'))}</a></p></article>"""
        for i in items
    )
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "NewsArticle", "headline": p.title,
        "description": p.summary, "datePublished": p.published_at.isoformat() if p.published_at else None,
        "author": {"@type": "Organization", "name": "Ascend"},
        "mainEntityOfPage": f"{settings.SITE_URL}/blog/{p.slug}",
    })
    body = f"""<span class="eyebrow">{"Weekly highlights" if p.kind == "weekly" else "What's new in AI"}</span><h1>{h(p.title)}</h1>
<p class="meta">{p.published_at.strftime('%d %b %Y') if p.published_at else ''} · <a href="/blog">All digests</a></p>
<p class="lede">{h(p.summary)}</p>{stories}{_cta(p)}
<script type="application/ld+json">{ld}</script>"""
    return _page(f"{p.title} | Ascend", p.summary[:300], body,
                 f"{settings.SITE_URL}/blog/{p.slug}", og_type="article")


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return f"User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {settings.SITE_URL}/sitemap.xml\n"


@router.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    posts = (db.query(Post).filter(Post.status == "published")
             .order_by(Post.published_at.desc()).all())
    urls = [f"<url><loc>{settings.SITE_URL}/</loc><changefreq>weekly</changefreq></url>",
            f"<url><loc>{settings.SITE_URL}/blog</loc><changefreq>daily</changefreq></url>"]
    urls += [f"<url><loc>{settings.SITE_URL}/blog/{h(p.slug)}</loc>"
             f"<lastmod>{p.published_at.date().isoformat()}</lastmod></url>" for p in posts if p.published_at]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(urls) + "</urlset>")
    return Response(content=xml, media_type="application/xml")
