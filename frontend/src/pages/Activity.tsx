import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getSummary,
  KIND_LABEL,
  onActivityChange,
  type ActivityKind,
  type ActivitySummary,
} from "../lib/activity";

export default function Activity() {
  const [s, setS] = useState<ActivitySummary>(() => getSummary());

  useEffect(() => {
    const refresh = () => setS(getSummary());
    refresh();
    return onActivityChange(refresh);
  }, []);

  const days = Object.keys(s.days)
    .filter((d) => s.days[d] > 0)
    .sort((a, b) => b.localeCompare(a));

  function fmt(dateKey: string): string {
    const [y, m, d] = dateKey.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  return (
    <div className="page activity-page">
      <Link to="/" className="back-link">
        ← Back to dashboard
      </Link>

      <div className="page__head">
        <div>
          <h1 className="page__title">Your activity</h1>
          <p className="page__subtitle">Every action you've logged, most recent first.</p>
        </div>
      </div>

      <section className="activity__xp-card activity__xp-card--wide">
        <div className="activity__level-badge">
          <span className="activity__level-num">{s.level.level}</span>
          <span className="activity__level-lbl">LEVEL</span>
        </div>
        <div className="activity__xp-main">
          <div className="activity__xp-top">
            <span className="activity__xp-value">{s.xp} XP</span>
            <span className="activity__xp-next">
              {s.level.intoLevel}/{s.level.levelSpan}
            </span>
          </div>
          <div className="progress-bar__track activity__xp-track">
            <div
              className="progress-bar__fill"
              style={{ width: `${s.level.percent}%` }}
            />
          </div>
          <span className="activity__xp-hint">
            {s.level.levelSpan - s.level.intoLevel} XP to level {s.level.level + 1}
          </span>
        </div>
      </section>

      <div className="stat-row activity-stats">
        <div className="stat">
          <span className="stat__value">🔥 {s.streak}</span>
          <span className="stat__label">Day streak</span>
        </div>
        <div className="stat">
          <span className="stat__value">{s.activeDays}</span>
          <span className="stat__label">Active days</span>
        </div>
        <div className="stat">
          <span className="stat__value">{s.xp}</span>
          <span className="stat__label">Total XP</span>
        </div>
      </div>

      <div className="section-head">
        <h2 className="section-head__title">History</h2>
      </div>

      {days.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon" aria-hidden="true">📭</div>
          <h3 className="empty-state__title">No activity yet</h3>
          <p className="empty-state__text">
            Create goals and complete tasks to build your streak.
          </p>
        </div>
      ) : (
        <ul className="timeline">
          {days.map((d) => {
            const detail = s.details[d];
            const chips = detail
              ? Object.entries(detail)
                  .filter(([, n]) => (n ?? 0) > 0)
                  .map(([k, n]) => `${n}× ${KIND_LABEL[k as ActivityKind]}`)
              : [`${s.days[d]} actions`];
            return (
              <li key={d} className="timeline__item">
                <span className="timeline__dot" aria-hidden="true" />
                <div className="timeline__body">
                  <div className="timeline__date">{fmt(d)}</div>
                  <div className="timeline__chips">
                    {chips.map((c, i) => (
                      <span key={i} className="timeline__chip">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
