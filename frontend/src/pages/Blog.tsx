import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getPost, listPosts } from "../api/endpoints";
import type { Post } from "../types";

/** SPA fallback for /blog and /blog/:slug. In production Caddy serves these
 *  paths server-rendered from the API (for SEO); this covers local dev and
 *  in-app navigation. */
export default function Blog() {
  const { slug } = useParams();
  const [posts, setPosts] = useState<Post[]>([]);
  const [post, setPost] = useState<Post | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    if (slug) {
      getPost(slug).then(setPost).catch(() => setError("Post not found."));
    } else {
      listPosts(30).then(setPosts).catch(() => setError("Could not load digests."));
    }
  }, [slug]);

  return (
    <div className="landing blog">
      <header className="landing__nav">
        <Link to="/" className="brand"><span className="brand__name">As<span className="brand__accent">cend</span></span></Link>
        <nav className="landing__links">
          <Link to="/blog">All digests</Link>
          <Link to="/register" className="btn btn--sm btn--primary">Start free</Link>
        </nav>
      </header>

      {error && <div className="alert alert--error">{error}</div>}

      {!slug && (
        <>
          <span className="eyebrow">Daily digest</span>
          <h1 className="landing__title">What's new in AI</h1>
          <p className="landing__sub">Five stories a day, one thing to learn from them.</p>
          {posts.map((p) => (
            <Link key={p.id} to={`/blog/${p.slug}`} className="digest-card">
              <span className="digest-card__date">{p.published_at?.slice(0, 10)}</span>
              <h3>{p.title}</h3>
              <p>{p.summary}</p>
            </Link>
          ))}
        </>
      )}

      {slug && post && (
        <article>
          <span className="eyebrow">What's new in AI</span>
          <h1 className="landing__title">{post.title}</h1>
          <p className="landing__muted">{post.published_at?.slice(0, 10)}</p>
          <p className="landing__sub">{post.summary}</p>
          {(post.items ?? []).map((i, idx) => (
            <div key={idx} className="digest-card digest-card--static">
              <h3>{i.headline}</h3>
              <p>{i.summary}</p>
              <p className="landing__muted">{i.why_it_matters}</p>
              <a href={i.source_url} target="_blank" rel="noopener nofollow">{i.source_name}</a>
            </div>
          ))}
          <div className="digest-cta">
            <span className="eyebrow">What to learn from this</span>
            {post.learn_next && <p>{post.learn_next}</p>}
            <Link
              to={`/register?role=${encodeURIComponent(post.learn_role || "AI Engineer")}`}
              className="btn btn--primary"
            >
              Build my {post.learn_role || "AI Engineer"} plan
            </Link>
          </div>
        </article>
      )}
    </div>
  );
}
