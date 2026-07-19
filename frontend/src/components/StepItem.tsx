import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  createTask,
  deleteStep,
  listTasks,
  updateStep,
} from "../api/endpoints";
import { logActivity } from "../lib/activity";
import { useConfirm, useToast } from "../context/ui";
import type { Step, Task } from "../types";
import TaskRow from "./TaskRow";

// Render any URL in a description as a clickable link (e.g. course links).
function linkifyDesc(text: string) {
  return text.split(/(https?:\/\/[^\s]+)/g).map((part, i) => {
    if (/^https?:\/\//.test(part)) {
      let label = part;
      try {
        label = new URL(part).hostname.replace(/^www\./, "");
      } catch {
        /* keep raw */
      }
      return (
        <a
          key={i}
          href={part}
          target="_blank"
          rel="noreferrer noopener"
          className="step__link"
        >
          {label} ↗
        </a>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

interface Props {
  step: Step;
  /** Notify the path level that step/task data changed (for refetch). */
  onChanged: () => void;
}

export default function StepItem({ step, onChanged }: Props) {
  const confirm = useConfirm();
  const { success, error } = useToast();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [expanded, setExpanded] = useState(true);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const [newTask, setNewTask] = useState("");
  const [adding, setAdding] = useState(false);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [busy, setBusy] = useState(false);

  const loadTasks = useCallback(async () => {
    try {
      const t = await listTasks(step.id);
      setTasks(t);
    } finally {
      setLoadingTasks(false);
    }
  }, [step.id]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  async function refresh() {
    await loadTasks();
    onChanged();
  }

  async function toggleStep() {
    setBusy(true);
    try {
      await updateStep(step.id, { is_done: !step.is_done });
      if (!step.is_done) logActivity("complete_step");
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function removeStep() {
    const ok = await confirm({
      title: "Delete step",
      message: `Delete step "${step.title}" and its tasks?`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    try {
      await deleteStep(step.id);
      success("Step deleted");
      onChanged();
    } catch (err) {
      error(err instanceof Error ? err.message : "Failed to delete step.");
    } finally {
      setBusy(false);
    }
  }

  async function addTask(e: FormEvent) {
    e.preventDefault();
    if (!newTask.trim()) return;
    setAdding(true);
    try {
      await createTask(step.id, { title: newTask.trim() });
      logActivity("task");
      setNewTask("");
      await refresh();
    } finally {
      setAdding(false);
    }
  }

  const doneCount = tasks.filter((t) => t.is_done).length;

  return (
    <div className={`step ${step.is_done ? "step--done" : ""}`}>
      <div className="step__head">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={step.is_done}
            onChange={toggleStep}
            disabled={busy}
          />
          <span className="checkbox__box" aria-hidden="true" />
        </label>
        <button
          className="step__toggle"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
        >
          <span className={`chevron ${expanded ? "chevron--open" : ""}`} aria-hidden="true">
            ▸
          </span>
          <span className="step__title">{step.title}</span>
        </button>
        <span className="step__count">
          {doneCount}/{tasks.length}
        </span>
        <button
          className="icon-btn"
          onClick={removeStep}
          disabled={busy}
          aria-label={`Delete step ${step.title}`}
          title="Delete step"
        >
          ×
        </button>
      </div>

      {step.description && expanded && (
        <p className="step__desc">{linkifyDesc(step.description)}</p>
      )}

      {expanded && (
        <div className="step__body">
          {loadingTasks ? (
            <p className="muted-note">Loading tasks…</p>
          ) : tasks.length === 0 ? (
            <p className="muted-note">No tasks yet.</p>
          ) : (
            <ul className="task-list">
              {tasks.map((task) => (
                <TaskRow key={task.id} task={task} onChanged={refresh} />
              ))}
            </ul>
          )}

          {showTaskForm ? (
            <form onSubmit={addTask} className="inline-form">
              <input
                type="text"
                value={newTask}
                onChange={(e) => setNewTask(e.target.value)}
                placeholder="Add a task…"
                autoFocus
              />
              <button
                type="submit"
                className="btn btn--soft btn--sm"
                disabled={adding || !newTask.trim()}
              >
                {adding ? "Adding…" : "Add"}
              </button>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => {
                  setShowTaskForm(false);
                  setNewTask("");
                }}
              >
                Cancel
              </button>
            </form>
          ) : (
            <button
              className="btn btn--soft btn--sm add-task-btn"
              onClick={() => setShowTaskForm(true)}
            >
              + Add task
            </button>
          )}
        </div>
      )}
    </div>
  );
}
