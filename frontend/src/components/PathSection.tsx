import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  createStep,
  deletePath,
  listSteps,
} from "../api/endpoints";
import { logActivity } from "../lib/activity";
import { useConfirm, useToast } from "../context/ui";
import type { LearningPath, Step } from "../types";
import StepItem from "./StepItem";

interface Props {
  path: LearningPath;
  /** Accordion: whether this path is the open one. */
  expanded: boolean;
  /** Toggle this path open/closed (accordion — parent-controlled). */
  onToggle: () => void;
  /** Called when this path is deleted so the parent can refetch. */
  onDeleted: () => void;
}

export default function PathSection({ path, expanded, onToggle, onDeleted }: Props) {
  const confirm = useConfirm();
  const { success, error } = useToast();
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(true);

  const [showStepForm, setShowStepForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [order, setOrder] = useState("");
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState(false);

  const loadSteps = useCallback(async () => {
    try {
      const s = await listSteps(path.id);
      // Sort by step_order for stable display.
      s.sort((a, b) => a.step_order - b.step_order || a.id - b.id);
      setSteps(s);
    } finally {
      setLoading(false);
    }
  }, [path.id]);

  useEffect(() => {
    loadSteps();
  }, [loadSteps]);

  async function refresh() {
    await loadSteps();
  }

  async function addStep(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      await createStep(path.id, {
        title: title.trim(),
        description: description.trim() || undefined,
        step_order: order ? Number(order) : undefined,
      });
      logActivity("step");
      setTitle("");
      setDescription("");
      setOrder("");
      setShowStepForm(false);
      await refresh();
    } finally {
      setSaving(false);
    }
  }

  async function removePath() {
    const ok = await confirm({
      title: "Delete path",
      message: `Delete "${path.title}" and everything under it? This can't be undone.`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    try {
      await deletePath(path.id);
      success("Path deleted");
      onDeleted();
    } catch (err) {
      error(err instanceof Error ? err.message : "Failed to delete path.");
    } finally {
      setBusy(false);
    }
  }

  const doneSteps = steps.filter((s) => s.is_done).length;

  return (
    <div className="path-card">
      <div className="path-card__head">
        <button
          className="path-card__toggle"
          onClick={onToggle}
          aria-expanded={expanded}
        >
          <span className={`chevron ${expanded ? "chevron--open" : ""}`} aria-hidden="true">
            ▸
          </span>
          <span>
            <span className="path-card__title">{path.title}</span>
            {path.description && (
              <span className="path-card__desc">{path.description}</span>
            )}
          </span>
        </button>
        <div className="path-card__head-right">
          <span className="path-card__count">
            {doneSteps}/{steps.length} steps
          </span>
          <button
            className="btn btn--danger-ghost btn--sm"
            onClick={removePath}
            disabled={busy}
          >
            Delete
          </button>
        </div>
      </div>

      {expanded && (
        <div className="path-card__body">
          {loading ? (
            <p className="muted-note">Loading steps…</p>
          ) : steps.length === 0 ? (
            <p className="muted-note">No steps yet — add one to get started.</p>
          ) : (
            <div className="step-list">
              {steps.map((step) => (
                <StepItem key={step.id} step={step} onChanged={refresh} />
              ))}
            </div>
          )}

          {showStepForm ? (
            <form onSubmit={addStep} className="nested-form">
              <div className="field-row">
                <label className="field field--grow">
                  <span className="field__label">Step title</span>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Learn TypeScript generics"
                    required
                    autoFocus
                  />
                </label>
                <label className="field field--order">
                  <span className="field__label">Order</span>
                  <input
                    type="number"
                    value={order}
                    onChange={(e) => setOrder(e.target.value)}
                    placeholder="#"
                    min={0}
                  />
                </label>
              </div>
              <label className="field">
                <span className="field__label">Description (optional)</span>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="A short note about this step"
                />
              </label>
              <div className="form__actions">
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => setShowStepForm(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn--primary btn--sm"
                  disabled={saving}
                >
                  {saving ? "Adding…" : "Add step"}
                </button>
              </div>
            </form>
          ) : (
            <button
              className="btn btn--soft btn--sm add-step-btn"
              onClick={() => setShowStepForm(true)}
            >
              + Add step
            </button>
          )}
        </div>
      )}
    </div>
  );
}
