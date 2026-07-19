import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  createPath,
  getGoal,
  listPaths,
} from "../api/endpoints";
import type { Goal, LearningPath } from "../types";
import PathSection from "../components/PathSection";
import SuggestionsWizard from "../components/SuggestionsWizard";

export default function GoalDetail() {
  const { id } = useParams<{ id: string }>();
  const goalId = Number(id);

  const [goal, setGoal] = useState<Goal | null>(null);
  const [paths, setPaths] = useState<LearningPath[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showPathForm, setShowPathForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  // Bumped only on suggestion adds so existing paths remount and show new steps.
  const [pathsVersion, setPathsVersion] = useState(0);

  const [params, setParams] = useSearchParams();
  const [showWizard, setShowWizard] = useState(false);
  // Accordion allows MULTIPLE paths open at once.
  const [openPathIds, setOpenPathIds] = useState<Set<number>>(new Set());

  // Auto-open the suggestions wizard when arriving from goal creation.
  useEffect(() => {
    if (params.get("suggest") === "1") {
      setShowWizard(true);
      params.delete("suggest");
      setParams(params, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Default the first path open once; drop ids for paths that no longer exist.
  const didInitOpen = useRef(false);
  useEffect(() => {
    setOpenPathIds((cur) => {
      const valid = new Set([...cur].filter((id) => paths.some((p) => p.id === id)));
      if (!didInitOpen.current && valid.size === 0 && paths.length) {
        valid.add(paths[0].id);
        didInitOpen.current = true;
      }
      return valid;
    });
  }, [paths]);

  const loadPaths = useCallback(async () => {
    const p = await listPaths(goalId);
    p.sort((a, b) => a.id - b.id);
    setPaths(p);
  }, [goalId]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setError(null);
      const [g] = await Promise.all([getGoal(goalId), loadPaths()]);
      setGoal(g);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load goal.");
    } finally {
      setLoading(false);
    }
  }, [goalId, loadPaths]);

  useEffect(() => {
    if (Number.isNaN(goalId)) {
      setError("Invalid goal.");
      setLoading(false);
      return;
    }
    load();
  }, [goalId, load]);

  async function addPath(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      await createPath(goalId, {
        title: title.trim(),
        description: description.trim() || undefined,
      });
      setTitle("");
      setDescription("");
      setShowPathForm(false);
      await loadPaths();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create path.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner" aria-label="Loading goal" />
      </div>
    );
  }

  if (error && !goal) {
    return (
      <div className="page">
        <div className="alert alert--error">{error}</div>
        <Link to="/" className="btn btn--ghost">
          ← Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="page">
      <Link to="/" className="back-link">
        ← Back to dashboard
      </Link>

      {error && <div className="alert alert--error">{error}</div>}

      {goal && (
        <div className="goal-hero">
          <div>
            <div className="goal-hero__top">
              <h1 className="page__title">{goal.role}</h1>
              <span
                className={`badge ${
                  goal.is_active ? "badge--active" : "badge--muted"
                }`}
              >
                {goal.is_active ? "Active" : "Paused"}
              </span>
            </div>
            <div className="goal-card__meta">
              <span className="meta-pill">{goal.hours_per_week} hrs/wk</span>
              <span className="meta-pill">{goal.duration_weeks} weeks</span>
              <span className="meta-pill">
                {paths.length} {paths.length === 1 ? "path" : "paths"}
              </span>
            </div>
          </div>
        </div>
      )}

      {goal && (
        <SuggestionsWizard
          open={showWizard}
          goalId={goalId}
          role={goal.role}
          existingPaths={paths}
          onClose={() => {
            setShowWizard(false);
            loadPaths();
            setPathsVersion((v) => v + 1);
          }}
          onAdded={() => {
            loadPaths();
            setPathsVersion((v) => v + 1);
          }}
        />
      )}

      <div className="section-head">
        <h2 className="section-head__title">Learning paths</h2>
        <div className="section-head__actions">
          <button className="btn btn--soft btn--sm" onClick={() => setShowWizard(true)}>
            ✨ Suggestions
          </button>
          {!showPathForm && (
            <button
              className="btn btn--primary btn--sm"
              onClick={() => setShowPathForm(true)}
            >
              + Add path
            </button>
          )}
        </div>
      </div>

      {showPathForm && (
        <form onSubmit={addPath} className="panel-form">
          <div className="field-row">
            <label className="field field--grow">
              <span className="field__label">Path title</span>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Core Frontend Fundamentals"
                required
                autoFocus
              />
            </label>
          </div>
          <label className="field">
            <span className="field__label">Description (optional)</span>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this path covers"
            />
          </label>
          <div className="form__actions">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setShowPathForm(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn--primary btn--sm"
              disabled={saving}
            >
              {saving ? "Adding…" : "Add path"}
            </button>
          </div>
        </form>
      )}

      {paths.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon" aria-hidden="true">
            🗺️
          </div>
          <h3 className="empty-state__title">No learning paths yet</h3>
          <p className="empty-state__text">
            Break this goal into learning paths, then add steps and tasks.
          </p>
        </div>
      ) : (
        <div className="path-list">
          {paths.map((path) => (
            <PathSection
              key={`${path.id}-${pathsVersion}`}
              path={path}
              expanded={openPathIds.has(path.id)}
              onToggle={() =>
                setOpenPathIds((cur) => {
                  const next = new Set(cur);
                  next.has(path.id) ? next.delete(path.id) : next.add(path.id);
                  return next;
                })
              }
              onDeleted={loadPaths}
            />
          ))}
        </div>
      )}
    </div>
  );
}
