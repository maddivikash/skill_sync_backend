import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getNotifications } from "../api/endpoints";
import type { AppNotification } from "../types";

/** Header bell: due-today and overdue items, same source as the daily email. */
export default function NotificationsBell() {
  const navigate = useNavigate();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  async function refresh() {
    try {
      const { items } = await getNotifications();
      setItems(items);
    } catch {
      /* header must never break on a failed poll */
    }
  }

  useEffect(() => {
    refresh();
    const onChange = () => refresh();
    window.addEventListener("skillsync:data-changed", onChange);
    const timer = window.setInterval(refresh, 5 * 60 * 1000); // gentle re-poll
    return () => {
      window.removeEventListener("skillsync:data-changed", onChange);
      window.clearInterval(timer);
    };
  }, []);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const fmt = (iso: string) =>
    new Date(iso + "T00:00:00").toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });

  return (
    <div className="notif" ref={wrapRef}>
      <button
        className="theme-toggle notif__btn"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notifications: ${items.length} due`}
        title="Notifications"
      >
        🔔
        {items.length > 0 && <span className="notif__badge">{items.length > 9 ? "9+" : items.length}</span>}
      </button>

      {open && (
        <div className="notif__panel" role="dialog" aria-label="Notifications">
          <div className="notif__head">Today's check-in</div>
          {items.length === 0 ? (
            <p className="notif__empty">
              Nothing due today. Enjoy the clear runway.
            </p>
          ) : (
            <ul className="notif__list">
              {items.map((n, i) => (
                <li key={i}>
                  <button
                    className="notif__item"
                    onClick={() => {
                      setOpen(false);
                      navigate(`/goals/${n.goal_id}`);
                    }}
                  >
                    <span className="notif__title">{n.title}</span>
                    <span className={`notif__meta ${n.overdue ? "is-overdue" : ""}`}>
                      {n.goal_role} ·{" "}
                      {n.overdue ? `was due ${fmt(n.due_date)}` : "due today"}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
