import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  createGoal,
  deleteGoal,
  getDashboard,
  listRoles,
  resetGoal,
} from "../api/endpoints";
import type { CatalogRole, Dashboard as DashboardData } from "../types";
import ProgressRing from "../components/ProgressRing";
import ProgressBar from "../components/ProgressBar";
import Modal from "../components/Modal";
import ActivitySidebar from "../components/ActivitySidebar";
import RoleCombobox from "../components/RoleCombobox";
import { logActivity } from "../lib/activity";
import { useConfirm, useToast } from "../context/ui";

export default function Dashboard() {
  const navigate = useNavigate();
  const confirm = useConfirm();
  const { success, error: toastError } = useToast();

  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [roles, setRoles] = useState<CatalogRole[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [role, setRole] = useState("");
  const [hours, setHours] = useState("5");
  const [weeks, setWeeks] = useState("12");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setData(await getDashboard());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    listRoles().then(setRoles).catch(() => setRoles([]));
  }, []);

  // Close the kebab menu on any outside click.
  useEffect(() => {
    if (menuOpenId === null) return;
    const close = () => setMenuOpenId(null);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menuOpenId]);

  function resetForm() {
    setRole("");
    setHours("5");
    setWeeks("12");
    setFormError(null);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const finalRole = role.trim();
    if (!finalRole) {
      setFormError("Please choose or enter a target role.");
      return;
    }
    setSaving(true);
    try {
      const g = await createGoal({
        role: finalRole,
        hours_per_week: Number(hours),
        duration_weeks: Number(weeks),
      });
      logActivity("goal");
      setModalOpen(false);
      resetForm();
      // Jump straight into the tailored suggestions wizard.
      navigate(`/goals/${g.id}?suggest=1`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create goal.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number, roleName: string) {
    setMenuOpenId(null);
    const ok = await confirm({
      title: "Delete goal",
      message: `Delete the goal "${roleName}" and all its content? This can't be undone.`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    setBusyId(id);
    try {
      await deleteGoal(id);
      success("Goal deleted");
      await load();
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Failed to delete goal.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleReset(id: number, roleName: string) {
    setMenuOpenId(null);
    const ok = await confirm({
      title: "Reset goal",
      message: `Remove ALL learning paths, steps and tasks under "${roleName}"? The goal itself stays. This can't be undone.`,
      confirmText: "Reset",
      danger: true,
    });
    if (!ok) return;
    setBusyId(id);
    try {
      await resetGoal(id);
      success("Goal reset");
      await load();
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Failed to reset goal.");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner" aria-label="Loading dashboard" />
      </div>
    );
  }

  const overall = data?.overall ?? { total_tasks: 0, done_tasks: 0, percent: 0 };
  const goals = data?.goals ?? [];

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <span className="eyebrow">Momentum for mastery</span>
          <h1 className="page__title">Your dashboard</h1>
          <p className="page__subtitle">
            Track progress across every learning goal in one place.
          </p>
        </div>
        <button
          className="btn btn--primary"
          onClick={() => {
            resetForm();
            setModalOpen(true);
          }}
        >
          + New goal
        </button>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <div className="dashboard-layout">
        <ActivitySidebar />
        <div className="dashboard-main">
          <section className="overview-card">
            <ProgressRing percent={overall.percent} size={168} stroke={13} label="complete" />
            <div className="overview-card__stats">
              <h2 className="overview-card__heading">Overall progress</h2>
              <p className="overview-card__desc">
                You've completed <strong>{overall.done_tasks}</strong> of{" "}
                <strong>{overall.total_tasks}</strong> tasks across{" "}
                <strong>{goals.length}</strong>{" "}
                {goals.length === 1 ? "goal" : "goals"}.
              </p>
              <div className="stat-row">
                <div className="stat">
                  <span className="stat__value">{goals.length}</span>
                  <span className="stat__label">Goals</span>
                </div>
                <div className="stat">
                  <span className="stat__value">{overall.done_tasks}</span>
                  <span className="stat__label">Tasks done</span>
                </div>
                <div className="stat">
                  <span className="stat__value">{overall.total_tasks}</span>
                  <span className="stat__label">Total tasks</span>
                </div>
              </div>
            </div>
          </section>

          <div className="section-head">
            <h2 className="section-head__title">Goals</h2>
          </div>

          {goals.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state__icon" aria-hidden="true">🎯</div>
              <h3 className="empty-state__title">No goals yet</h3>
              <p className="empty-state__text">
                Create your first learning goal to start building a plan.
              </p>
              <button
                className="btn btn--primary"
                onClick={() => {
                  resetForm();
                  setModalOpen(true);
                }}
              >
                + New goal
              </button>
            </div>
          ) : (
            <div className="goal-grid">
              {goals.map((goal) => (
                <div
                  key={goal.id}
                  className={`goal-card goal-card--clickable ${
                    busyId === goal.id ? "is-busy" : ""
                  }`}
                  role="button"
                  tabIndex={0}
                  onClick={() => navigate(`/goals/${goal.id}`)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") navigate(`/goals/${goal.id}`);
                  }}
                >
                  <div className="goal-card__top">
                    <span className="goal-card__title">{goal.role}</span>
                    <div className="goal-card__top-right">
                      <span
                        className={`badge ${
                          goal.is_active ? "badge--active" : "badge--muted"
                        }`}
                      >
                        {goal.is_active ? "Active" : "Paused"}
                      </span>
                      <div
                        className="kebab"
                        onClick={(e) => e.stopPropagation()}
                        onMouseDown={(e) => e.stopPropagation()}
                      >
                        <button
                          className="icon-btn kebab__btn"
                          aria-label="Goal actions"
                          onClick={() =>
                            setMenuOpenId((cur) => (cur === goal.id ? null : goal.id))
                          }
                        >
                          ⋮
                        </button>
                        {menuOpenId === goal.id && (
                          <div className="kebab__menu" role="menu">
                            <button
                              className="kebab__item"
                              role="menuitem"
                              onClick={() => handleReset(goal.id, goal.role)}
                            >
                              ♻️ Reset paths
                            </button>
                            <button
                              className="kebab__item kebab__item--danger"
                              role="menuitem"
                              onClick={() => handleDelete(goal.id, goal.role)}
                            >
                              🗑️ Delete goal
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="goal-card__meta">
                    <span className="meta-pill">{goal.hours_per_week} hrs/wk</span>
                    <span className="meta-pill">{goal.duration_weeks} weeks</span>
                    <span className="meta-pill">
                      {goal.paths_count} {goal.paths_count === 1 ? "path" : "paths"}
                    </span>
                  </div>

                  <div className="goal-card__progress">
                    <div className="goal-card__progress-head">
                      <span>Progress</span>
                      <span className="goal-card__progress-count">
                        {goal.progress.done_tasks}/{goal.progress.total_tasks} tasks
                      </span>
                    </div>
                    <ProgressBar percent={goal.progress.percent} showValue />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <Modal
        open={modalOpen}
        title="Create a new goal"
        onClose={() => setModalOpen(false)}
      >
        {formError && <div className="alert alert--error">{formError}</div>}
        <form onSubmit={handleCreate} className="form">
          <label className="field">
            <span className="field__label">Target role</span>
            <RoleCombobox roles={roles} value={role} onChange={setRole} />
            <span className="field__hint">
              Search a preset role or type your own — you'll get tailored
              suggestions next.
            </span>
          </label>
          <div className="field-row">
            <label className="field">
              <span className="field__label">Hours / week</span>
              <input
                type="number"
                min={1}
                max={168}
                value={hours}
                onChange={(e) => setHours(e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span className="field__label">Duration (weeks)</span>
              <input
                type="number"
                min={1}
                max={520}
                value={weeks}
                onChange={(e) => setWeeks(e.target.value)}
                required
              />
            </label>
          </div>
          <div className="form__actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setModalOpen(false)}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn--primary" disabled={saving}>
              {saving ? "Creating…" : "Create goal"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
