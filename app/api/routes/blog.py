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
:root{--bg:#f4f4fb;--surface:#fff;--border:#e8e6f3;--text:#1b1a2e;--muted:#5d5b78;--brand:#6a3bf2;--brand-soft:#f0ebfe}
@media(prefers-color-scheme:dark){:root{--bg:#0a0912;--surface:#15131f;--border:#2a2740;--text:#ecebf5;--muted:#a3a0bd;--brand:#8a82ff;--brand-soft:#23233c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
a{color:var(--brand)}.wrap{max-width:760px;margin:0 auto;padding:32px 20px 64px}
header.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:36px}
.brand{font-weight:800;font-size:22px;text-decoration:none;color:var(--text)}.brand b{color:var(--brand)}
.btn{display:inline-block;background:var(--brand);color:#fff;text-decoration:none;padding:10px 18px;border-radius:999px;font-weight:600}
.eyebrow{text-transform:uppercase;letter-spacing:.08em;font-size:12px;color:var(--brand);font-weight:700}
h1{font-size:34px;line-height:1.2;margin:8px 0 12px}h2{font-size:20px;margin:0 0 6px}
.lede{color:var(--muted);font-size:18px}.meta{color:var(--muted);font-size:14px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:20px 22px;margin:18px 0}
.card p{margin:6px 0}.why{color:var(--muted)}.src{font-size:14px}
.cta{background:var(--brand-soft);border:1px solid var(--border);border-radius:16px;padding:22px;margin-top:32px}
.cta h3{margin:0 0 8px}.list a.title{font-size:20px;font-weight:700;text-decoration:none;color:var(--text)}
footer{margin-top:48px;color:var(--muted);font-size:14px}
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
<style>{CSS}</style></head><body><div class="wrap">
<header class="top"><a class="brand" href="/">As<b>cend</b></a>
<nav><a href="/blog" style="margin-right:16px">What's new in AI</a><a class="btn" href="/register">Start free</a></nav></header>
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
    posts = (db.query(Post).filter(Post.status == "published")
             .order_by(Post.published_at.desc()).limit(30).all())
    cards = "".join(
        f"""<article class="card list"><a class="title" href="/blog/{h(p.slug)}">{h(p.title)}</a>
<p class="meta">{p.published_at.strftime('%d %b %Y') if p.published_at else ''}</p>
<p>{h(p.summary)}</p></article>""" for p in posts
    ) or "<p class='lede'>First digest lands soon.</p>"
    body = f"""<span class="eyebrow">Daily digest</span><h1>What's new in AI</h1>
<p class="lede">Five stories a day, one thing to learn from them. Written for people building a career, not chasing hype.</p>{cards}"""
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
    body = f"""<span class="eyebrow">What's new in AI</span><h1>{h(p.title)}</h1>
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
