import { useState } from "react";
import { deleteTask, updateTask } from "../api/endpoints";
import { logActivity } from "../lib/activity";
import { useConfirm, useToast } from "../context/ui";
import type { Task } from "../types";

interface Props {
  task: Task;
  onChanged: () => void;
}

export default function TaskRow({ task, onChanged }: Props) {
  const confirm = useConfirm();
  const { success, error } = useToast();
  const [busy, setBusy] = useState(false);

  async function toggle() {
    setBusy(true);
    try {
      await updateTask(task.id, { is_done: !task.is_done });
      if (!task.is_done) logActivity("complete_task");
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    const ok = await confirm({
      title: "Delete task",
      message: `Delete task "${task.title}"?`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    try {
      await deleteTask(task.id);
      success("Task deleted");
      onChanged();
    } catch (err) {
      error(err instanceof Error ? err.message : "Failed to delete task.");
    } finally {
      setBusy(false);
    }
  }

  // Due-date chip: "due Jul 30", red when overdue and not done.
  let dueChip = null;
  if (task.due_date) {
    const due = new Date(task.due_date + "T00:00:00");
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const overdue = !task.is_done && due < today;
    const label = due.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
    dueChip = (
      <span className={`task-row__due ${overdue ? "is-overdue" : ""}`}>
        {overdue ? `was due ${label}` : `due ${label}`}
      </span>
    );
  }

  return (
    <li className={`task-row ${task.is_done ? "task-row--done" : ""}`}>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={task.is_done}
          onChange={toggle}
          disabled={busy}
        />
        <span className="checkbox__box" aria-hidden="true" />
        <span className="task-row__title">{task.title}</span>
      </label>
      {dueChip}
      <button
        className="icon-btn"
        onClick={remove}
        disabled={busy}
        aria-label={`Delete task ${task.title}`}
        title="Delete task"
      >
        ×
      </button>
    </li>
  );
}
