import { useEffect, useRef, useState } from "react";
import {
  createPath,
  createStep,
  deletePath,
  deleteStep,
  getSuggestions,
} from "../api/endpoints";
import { logActivity } from "../lib/activity";
import { useToast } from "../context/ui";
import Modal from "./Modal";
import type { CatalogCategory, CatalogItem, LearningPath, RoleSuggestions } from "../types";

const STEPS: { cat: CatalogCategory; title: string; icon: string; plural: string }[] = [
  { cat: "skill", title: "Skills to learn", icon: "🧠", plural: "Skills" },
  { cat: "course", title: "Courses", icon: "🎓", plural: "Courses" },
  { cat: "tool", title: "Tools", icon: "🛠️", plural: "Tools" },
  { cat: "project", title: "Projects to build", icon: "🚀", plural: "Projects" },
];

interface Props {
  open: boolean;
  goalId: number;
  role: string;
  /** Paths that already exist on the goal, so we merge into them
      instead of creating duplicate "Skills"/"Courses"/… paths. */
  existingPaths: LearningPath[];
  onClose: () => void;
  onAdded: () => void;
}

function courseMeta(s: CatalogItem): string {
  const parts: string[] = [];
  if (s.provider) parts.push(s.provider);
  if (s.estimated_hours) parts.push(`~${s.estimated_hours}h`);
  return parts.join(" · ");
}

export default function SuggestionsWizard({ open, goalId, role, existingPaths, onClose, onAdded }: Props) {
  const { success, error } = useToast();
  const [data, setData] = useState<RoleSuggestions | null>(null);
  const [loading, setLoading] = useState(true);
  const [idx, setIdx] = useState(0);
  const [busy, setBusy] = useState<number | null>(null);
  // Track what was created for each catalog item so it can be removed/undone.
  const [added, setAdded] = useState<
    Record<number, { kind: "step" | "path"; id: number }>
  >({});
  const pathCache = useRef<Record<string, number>>({});

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setIdx(0);
    setAdded({});
    pathCache.current = {};
    getSuggestions(role)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [open, role]);

  if (!open) return null;

  const step = STEPS[idx];
  const items: CatalogItem[] = data?.items[step.cat] ?? [];
  const isLast = idx === STEPS.length - 1;

  async function ensurePath(cat: CatalogCategory, plural: string): Promise<number> {
    // Same-session cache (already added something in this category).
    if (pathCache.current[cat]) return pathCache.current[cat];
    // Reuse a matching path from a previous visit instead of duplicating it.
    const existing = existingPaths.find(
      (p) => p.title.trim().toLowerCase() === plural.toLowerCase()
    );
    if (existing) {
      pathCache.current[cat] = existing.id;
      return existing.id;
    }
    const p = await createPath(goalId, {
      title: plural,
      description: `Suggested ${plural.toLowerCase()} for ${role}`,
    });
    pathCache.current[cat] = p.id;
    return p.id;
  }

  async function add(s: CatalogItem) {
    setBusy(s.id);
    try {
      let entry: { kind: "step" | "path"; id: number };
      if (step.cat === "project") {
        const p = await createPath(goalId, {
          title: s.name,
          description: s.description || undefined,
        });
        if (s.steps) {
          for (let i = 0; i < s.steps.length; i++) {
            await createStep(p.id, { title: s.steps[i], step_order: i + 1 });
          }
        }
        logActivity("project");
        entry = { kind: "path", id: p.id };
      } else {
        const pathId = await ensurePath(step.cat, step.plural);
        // Keep the course link in the description so it stays clickable.
        const desc =
          step.cat === "course"
            ? [courseMeta(s), s.url].filter(Boolean).join(" · ")
            : s.description || undefined;
        const created = await createStep(pathId, {
          title: s.name,
          description: desc || undefined,
        });
        logActivity("step");
        entry = { kind: "step", id: created.id };
      }
      setAdded((prev) => ({ ...prev, [s.id]: entry }));
      success(`Added "${s.name}"`);
      onAdded();
    } catch (err) {
      error(err instanceof Error ? err.message : "Failed to add.");
    } finally {
      setBusy(null);
    }
  }

  async function remove(s: CatalogItem) {
    const entry = added[s.id];
    if (!entry) return;
    setBusy(s.id);
    try {
      if (entry.kind === "path") await deletePath(entry.id);
      else await deleteStep(entry.id);
      setAdded((prev) => {
        const next = { ...prev };
        delete next[s.id];
        return next;
      });
      onAdded();
    } catch (err) {
      error(err instanceof Error ? err.message : "Failed to remove.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Modal open={open} title="Recommended for your goal" onClose={onClose}>
      <div className="wizard">
        <div className="wizard__tabs" role="tablist" aria-label="Suggestion categories">
          {STEPS.map((s, i) => (
            <button
              key={s.cat}
              type="button"
              role="tab"
              aria-selected={i === idx}
              className={`wizard__tab ${i === idx ? "is-active" : ""}`}
              onClick={() => setIdx(i)}
            >
              <span aria-hidden="true">{s.icon}</span>
              <span className="wizard__tab-label">{s.plural}</span>
            </button>
          ))}
        </div>

        <div className="wizard__head">
          <h3 className="wizard__title">
            <span aria-hidden="true">{step.icon}</span> {step.title}
          </h3>
          <span className="wizard__count">
            {idx + 1} / {STEPS.length}
          </span>
        </div>
        <p className="wizard__sub">
          {data?.matched ? (
            <>Curated for <strong>{data.label}</strong>. Add what fits — you can change everything later.</>
          ) : (
            <>General picks for “{role}”. Add what fits — you can change everything later.</>
          )}
        </p>

        {loading ? (
          <p className="muted-note">Loading suggestions…</p>
        ) : (
          <div className="wizard__grid">
            {items.length === 0 && (
              <p className="muted-note">No suggestions for this category.</p>
            )}
            {items.map((s) => {
              const isAdded = !!added[s.id];
              return (
                <div key={s.id} className={`suggest-card ${isAdded ? "is-added" : ""}`}>
                  <div className="suggest-card__body">
                    <span className="suggest-card__name">{s.name}</span>
                    {step.cat === "course" && courseMeta(s) && (
                      <span className="suggest-card__meta">{courseMeta(s)}</span>
                    )}
                    {s.description && step.cat !== "course" && (
                      <span className="suggest-card__desc">{s.description}</span>
                    )}
                    {step.cat === "project" && s.steps && (
                      <span className="suggest-card__meta">{s.steps.length} milestones</span>
                    )}
                    {s.url && (
                      <a
                        className="suggest-card__link"
                        href={s.url}
                        target="_blank"
                        rel="noreferrer noopener"
                      >
                        View course ↗
                      </a>
                    )}
                  </div>
                  {isAdded ? (
                    <button
                      className="btn btn--sm btn--added"
                      disabled={busy === s.id}
                      onClick={() => remove(s)}
                      title="Remove"
                    >
                      {busy === s.id ? "…" : "✓ Added ✕"}
                    </button>
                  ) : (
                    <button
                      className="btn btn--sm btn--soft"
                      disabled={busy === s.id}
                      onClick={() => add(s)}
                    >
                      {busy === s.id ? "Adding…" : "+ Add"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="wizard__footer">
          <button className="btn btn--ghost" onClick={onClose}>
            {isLast ? "Finish" : "Skip all"}
          </button>
          <div className="wizard__nav">
            {idx > 0 && (
              <button className="btn btn--ghost" onClick={() => setIdx((i) => i - 1)}>
                ← Back
              </button>
            )}
            {isLast ? (
              <button className="btn btn--primary" onClick={onClose}>
                Done
              </button>
            ) : (
              <button className="btn btn--primary" onClick={() => setIdx((i) => i + 1)}>
                Next →
              </button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
