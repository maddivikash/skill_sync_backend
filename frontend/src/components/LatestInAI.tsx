import { useEffect, useState } from "react";
import { listPosts } from "../api/endpoints";
import type { Post } from "../types";

/** Dashboard widget: latest published digests. Hidden when none exist. */
export default function LatestInAI() {
  const [posts, setPosts] = useState<Post[]>([]);
  useEffect(() => {
    listPosts(3).then(setPosts).catch(() => setPosts([]));
  }, []);
  if (posts.length === 0) return null;
  return (
    <section className="latest-ai">
      <div className="section-head">
        <h2 className="section-head__title">What's new in AI</h2>
        <a href="/blog">All digests</a>
      </div>
      <ul className="latest-ai__list">
        {posts.map((p) => (
          <li key={p.id}>
            <a href={`/blog/${p.slug}`}>
              <span className="latest-ai__date">
                {p.published_at ? new Date(p.published_at).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : ""}
              </span>
              <span className="latest-ai__title">{p.title}</span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
