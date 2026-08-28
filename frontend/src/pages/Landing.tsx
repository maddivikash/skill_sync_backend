import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPosts } from "../api/endpoints";
import type { Post } from "../types";
import { useTheme } from "../context/theme";

const ROLES = ["AI Engineer", "Data Scientist", "DevOps Engineer", "Product Manager", "UPSC"];

export default function Landing() {
  const { theme, toggle } = useTheme();
  const [posts, setPosts] = useState<Post[]>([]);

  useEffect(() => {
    listPosts(3).then(setPosts).catch(() => setPosts([]));
  }, []);

  return (
    <div className="landing">
      <header className="landing__nav">
        <Link to="/" className="brand" aria-label="Ascend home">
          <span className="brand__mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none">
              <path d="M4 13l4 4L20 5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <span className="brand__name">As<span className="brand__accent">cend</span></span>
        </Link>
        <nav className="landing__links">
          <a href="/blog">What's new in AI</a>
          <button className="theme-toggle" onClick={toggle} aria-label="Toggle theme">
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
          <Link to="/login" className="btn btn--sm">Sign in</Link>
          <Link to="/register" className="btn btn--sm btn--primary">Start free</Link>
        </nav>
      </header>

      <section className="landing__hero">
        <span className="eyebrow">Momentum for mastery</span>
        <h1 className="landing__title">
          Pick a role.
          <br />
          <em>Get a plan you can actually finish.</em>
        </h1>
        <p className="landing__sub">
          Ascend turns any target role, from AI Engineer to UPSC, into skills, courses, tools and
          projects, broken into weekly steps. An AI coach keeps you moving. Streaks and XP make
          finishing feel good.
        </p>
        <div className="landing__cta-row">
          <Link to="/register" className="btn btn--primary landing__cta">Build my plan</Link>
          <a href="/blog" className="btn">Read today's AI digest</a>
        </div>
        <div className="landing__roles">
          {ROLES.map((r) => (
            <Link key={r} to={`/register?role=${encodeURIComponent(r)}`} className="chip">
              {r}
            </Link>
          ))}
        </div>
      </section>

      <section className="landing__features">
        <div className="feature">
          <h3>Structured paths</h3>
          <p>A 130 role catalog plus AI generated paths for anything else. Steps, tasks, deadlines.</p>
        </div>
        <div className="feature">
          <h3>An AI coach that does things</h3>
          <p>Ask what to learn next and it adds the steps for you. Learn Studio tutors you per step.</p>
        </div>
        <div className="feature">
          <h3>Accountability built in</h3>
          <p>Due dates, reminders, a heatmap of your effort, and XP only for finishing.</p>
        </div>
      </section>

      <section className="landing__digest">
        <div className="section-head">
          <h2 className="section-head__title">What's new in AI</h2>
          <a href="/blog">All digests</a>
        </div>
        {posts.length === 0 ? (
          <p className="landing__muted">Five stories a day, one thing to learn from them. First digest lands soon.</p>
        ) : (
          <div className="digest-grid">
            {posts.map((p) => (
              <a key={p.id} href={`/blog/${p.slug}`} className="digest-card">
                <span className="digest-card__date">
                  {p.published_at ? new Date(p.published_at).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : ""}
                </span>
                <h3>{p.title}</h3>
                <p>{p.summary}</p>
              </a>
            ))}
          </div>
        )}
      </section>

      <footer className="landing__footer">
        <span>Ascend · ascenddaily.in</span>
        <span>
          <a href="/blog">Digest</a> · <Link to="/login">Sign in</Link> · <Link to="/register">Register</Link>
        </span>
      </footer>
    </div>
  );
}
