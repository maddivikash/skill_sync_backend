import { useEffect, useState, type MouseEvent as ReactMouseEvent } from "react";
import { Link } from "react-router-dom";
import {
  dayKey,
  getSummary,
  KIND_LABEL,
  onActivityChange,
  type ActivityKind,
  type ActivitySummary,
} from "../lib/activity";

const WEEKS = 14; // ~3.5 months of history
const DAY_LABELS = ["", "Mon", "", "Wed", "", "Fri", ""];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

interface Cell {
  key: string;
  date: Date;
  count: number;
  future: boolean;
}

interface Tip {
  date: string;
  lines: string[];
  x: number;
  y: number;
}

function buildGrid(days: Record<string, number>): Cell[][] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const end = new Date(today);
  end.setDate(end.getDate() + (6 - end.getDay()));
  const start = new Date(end);
  start.setDate(start.getDate() - (WEEKS * 7 - 1));

  const columns: Cell[][] = [];
  const cursor = new Date(start);
  for (let w = 0; w < WEEKS; w++) {
    const col: Cell[] = [];
    for (let d = 0; d < 7; d++) {
      const date = new Date(cursor);
      col.push({
        key: dayKey(date),
        date,
        count: days[dayKey(date)] ?? 0,
        future: date.getTime() > today.getTime(),
      });
      cursor.setDate(cursor.getDate() + 1);
    }
    columns.push(col);
  }
  return columns;
}

function level(count: number): number {
  if (count <= 0) return 0;
  if (count === 1) return 1;
  if (count <= 3) return 2;
  if (count <= 5) return 3;
  return 4;
}

export default function ActivitySidebar() {
  const [summary, setSummary] = useState<ActivitySummary>(() => getSummary());
  const [tip, setTip] = useState<Tip | null>(null);

  useEffect(() => {
    const refresh = () => setSummary(getSummary());
    refresh();
    return onActivityChange(refresh);
  }, []);

  const grid = buildGrid(summary.days);
  const lvl = summary.level;

  // Month label per column: show the abbrev where a new month starts.
  const monthLabels = grid.map((col, i) => {
    const m = col[0].date.getMonth();
    const prev = i > 0 ? grid[i - 1][0].date.getMonth() : -1;
    return m !== prev ? MONTHS[m] : "";
  });

  function tipData(cell: Cell): { date: string; lines: string[] } {
    const d = cell.date.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
    if (cell.count === 0) return { date: d, lines: ["No activity"] };
    const detail = summary.details[cell.key];
    if (detail) {
      const parts = Object.entries(detail)
        .filter(([, n]) => (n ?? 0) > 0)
        .map(([k, n]) => `${n}× ${KIND_LABEL[k as ActivityKind]}`);
      if (parts.length) return { date: d, lines: parts };
    }
    return {
      date: d,
      lines: [`${cell.count} ${cell.count === 1 ? "action" : "actions"}`],
    };
  }

  function showTip(e: ReactMouseEvent<HTMLElement>, cell: Cell) {
    if (cell.future) return;
    const r = e.currentTarget.getBoundingClientRect();
    const t = tipData(cell);
    setTip({ ...t, x: r.left + r.width / 2, y: r.top });
  }

  return (
    <aside className="activity">
      <Link to="/activity" className="activity__xp-card activity__xp-card--link" title="View full activity">
        <div className="activity__level-badge">
          <span className="activity__level-num">{lvl.level}</span>
          <span className="activity__level-lbl">LEVEL</span>
        </div>
        <div className="activity__xp-main">
          <div className="activity__xp-top">
            <span className="activity__xp-value">{summary.xp} XP</span>
            <span className="activity__xp-next">
              {lvl.intoLevel}/{lvl.levelSpan}
            </span>
          </div>
          <div className="progress-bar__track activity__xp-track">
            <div className="progress-bar__fill" style={{ width: `${lvl.percent}%` }} />
          </div>
          <span className="activity__xp-hint">
            {lvl.levelSpan - lvl.intoLevel} XP to level {lvl.level + 1} · view all →
          </span>
        </div>
      </Link>

      <div className="activity__stats">
        <div className="activity__stat">
          <span className="activity__stat-value">
            <span aria-hidden="true">🔥</span> {summary.streak}
          </span>
          <span className="activity__stat-label">Day streak</span>
        </div>
        <div className="activity__stat">
          <span className="activity__stat-value">{summary.activeDays}</span>
          <span className="activity__stat-label">Active days</span>
        </div>
        <div className="activity__stat">
          <span className={`activity__today ${summary.todayActive ? "is-on" : ""}`}>
            {summary.todayActive ? "Active" : "Idle"}
          </span>
          <span className="activity__stat-label">Today</span>
        </div>
      </div>

      <div className="activity__heat">
        <div className="activity__heat-head">
          <span>Activity</span>
          <span className="activity__heat-sub">last {WEEKS} weeks</span>
        </div>
        <div className="activity__heat-body">
          <div className="activity__weekdays" aria-hidden="true">
            {DAY_LABELS.map((d, i) => (
              <span key={i}>{d}</span>
            ))}
          </div>
          <div className="activity__grid-area">
            <div className="activity__months" aria-hidden="true">
              {monthLabels.map((m, i) => (
                <span key={i} className="activity__month">
                  {m}
                </span>
              ))}
            </div>
            <div className="activity__grid" role="img" aria-label="Activity heatmap">
              {grid.map((col, ci) => (
                <div key={ci} className="activity__col">
                  {col.map((cell) => (
                    <span
                      key={cell.key}
                      className={`activity__cell ${
                        cell.future ? "is-future" : `lvl-${level(cell.count)}`
                      }`}
                      onMouseEnter={(e) => showTip(e, cell)}
                      onMouseLeave={() => setTip(null)}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="activity__legend">
          <span>Less</span>
          <span className="activity__cell lvl-0" />
          <span className="activity__cell lvl-1" />
          <span className="activity__cell lvl-2" />
          <span className="activity__cell lvl-3" />
          <span className="activity__cell lvl-4" />
          <span>More</span>
        </div>
      </div>

      {tip && (
        <div
          className="heat-tip"
          style={{ left: tip.x, top: tip.y }}
          role="tooltip"
        >
          <div className="heat-tip__date">{tip.date}</div>
          <ul className="heat-tip__list">
            {tip.lines.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
