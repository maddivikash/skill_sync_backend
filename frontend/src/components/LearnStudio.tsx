import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  learnPlan,
  learnTurn,
  updateStep,
  updateTask,
  type ChatMsg,
  type LearnMode,
  type LearnPlan,
  type LearnTask,
} from "../api/endpoints";
import { logActivity } from "../lib/activity";
import { useToast } from "../context/ui";

// Minimal, safe markdown -> HTML (escape first, then bold/code/bullets/breaks).
function fmt(text: string): string {
  const esc = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return esc
    .replace(/^\s*#{1,6}\s*/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^\s*[-*]\s+/gm, "• ")
    .replace(/\n/g, "<br/>");
}

interface Props {
  stepId: number;
  stepTitle: string;
  onChanged: () => void;
  onClose: () => void;
}

type Phase = "mode" | "tasks" | "learning" | "done";

export default function LearnStudio({
  stepId,
  stepTitle,
  onChanged,
  onClose,
}: Props) {
  const { error } = useToast();
  const [phase, setPhase] = useState<Phase>("mode");
  const [mode, setMode] = useState<LearnMode>("guided");
  const [plan, setPlan] = useState<LearnPlan | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [queue, setQueue] = useState<LearnTask[]>([]);
  const [idx, setIdx] = useState(0);
  const [threads, setThreads] = useState<Record<number, ChatMsg[]>>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [planning, setPlanning] = useState(false);
  const kicked = useRef<Set<number>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  const current = queue[idx];
  const thread = current ? threads[current.id] ?? [] : [];

  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [thread, busy, phase]);

  // Pick a mode -> generate (or resume) the task list.
  async function chooseMode(m: LearnMode) {
    setMode(m);
    setPlanning(true);
    try {
      const p = await learnPlan(stepId);
      setPlan(p);
      setSelected(new Set(p.tasks.filter((t) => !t.is_done).map((t) => t.id)));
      setPhase("tasks");
    } catch (err) {
      error(err instanceof Error ? err.message : "Couldn't build a plan.");
    } finally {
      setPlanning(false);
    }
  }

  function toggleTask(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function startLearning() {
    if (!plan) return;
    const chosen = plan.tasks.filter((t) => selected.has(t.id));
    if (!chosen.length) return;
    setQueue(chosen);
    setIdx(0);
    setPhase("learning");
  }

  // First lesson for a task, fetched once when it becomes current.
  const kickoff = useCallback(
    async (task: LearnTask) => {
      if (kicked.current.has(task.id)) return;
      kicked.current.add(task.id);
      setBusy(true);
      try {
        const { reply } = await learnTurn({
          step_id: stepId,
          task_id: task.id,
          mode,
          messages: [],
        });
        setThreads((t) => ({
          ...t,
          [task.id]: [{ role: "assistant", content: reply }],
        }));
      } catch (err) {
        error(err instanceof Error ? err.message : "The coach is unavailable.");
        kicked.current.delete(task.id); // allow retry
      } finally {
        setBusy(false);
      }
    },
    [stepId, mode, error]
  );

  useEffect(() => {
    if (phase === "learning" && current) kickoff(current);
  }, [phase, current, kickoff]);

  async function send(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy || !current) return;
    const history = [...thread, { role: "user" as const, content: text }];
    setThreads((t) => ({ ...t, [current.id]: history }));
    setInput("");
    setBusy(true);
    try {
      const { reply } = await learnTurn({
        step_id: stepId,
        task_id: current.id,
        mode,
        messages: history,
      });
      setThreads((t) => ({
        ...t,
        [current.id]: [...history, { role: "assistant", content: reply }],
      }));
    } catch (err) {
      error(err instanceof Error ? err.message : "The coach is unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function markDoneNext() {
    if (!current) return;
    setBusy(true);
    try {
      if (!current.is_done) {
        await updateTask(current.id, { is_done: true });
        logActivity("complete_task");
      }
      onChanged();
      window.dispatchEvent(new Event("skillsync:data-changed"));
      if (idx + 1 >= queue.length) setPhase("done");
      else setIdx((i) => i + 1);
    } catch (err) {
      error(err instanceof Error ? err.message : "Couldn't save progress.");
    } finally {
      setBusy(false);
    }
  }

  async function completeStep() {
    setBusy(true);
    try {
      await updateStep(stepId, { is_done: true });
      logActivity("complete_step");
      onChanged();
      window.dispatchEvent(new Event("skillsync:data-changed"));
      onClose();
    } catch (err) {
      error(err instanceof Error ? err.message : "Couldn't mark it complete.");
    } finally {
      setBusy(false);
    }
  }

  const cat = plan?.category ?? "topic";

  return (
    <div className="learn-overlay" onClick={onClose}>
      <div
        className="learn-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <header className="learn-modal__head">
          <div>
            <span className="learn-modal__eyebrow">Learn with coach</span>
            <h2 className="learn-modal__title">{stepTitle}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        {/* ---- Phase: choose a mode ---- */}
        {phase === "mode" && (
          <div className="learn-modal__body learn-modes">
            <p className="learn-lead">
              How would you like to learn this? Pick a style to begin.
            </p>
            <div className="learn-mode-grid">
              <button
                className="learn-mode-card"
                onClick={() => chooseMode("guided")}
                disabled={planning}
              >
                <span className="learn-mode-card__icon">📖</span>
                <span className="learn-mode-card__name">Guided</span>
                <span className="learn-mode-card__desc">
                  The coach explains each task with an example. You read, ask
                  follow ups, then move on. Calm and steady.
                </span>
              </button>
              <button
                className="learn-mode-card"
                onClick={() => chooseMode("interactive")}
                disabled={planning}
              >
                <span className="learn-mode-card__icon">💬</span>
                <span className="learn-mode-card__name">Interactive</span>
                <span className="learn-mode-card__desc">
                  The coach teaches, then quizzes you and checks your answers
                  before moving on. More hands on.
                </span>
              </button>
            </div>
            {planning && <p className="learn-lead">Building your task list…</p>}
          </div>
        )}

        {/* ---- Phase: pick tasks ---- */}
        {phase === "tasks" && plan && (
          <div className="learn-modal__body">
            <p className="learn-lead">
              Here's a plan for <strong>{stepTitle}</strong>. Pick what you want
              to work through, then start.
            </p>
            <ul className="learn-task-picker">
              {plan.tasks.map((t) => (
                <li key={t.id}>
                  <label className={t.is_done ? "is-done" : ""}>
                    <input
                      type="checkbox"
                      checked={selected.has(t.id)}
                      onChange={() => toggleTask(t.id)}
                    />
                    <span>{t.title}</span>
                    {t.is_done && <span className="learn-chip-done">done</span>}
                  </label>
                </li>
              ))}
            </ul>
            <div className="learn-modal__actions">
              <button className="btn btn--ghost btn--sm" onClick={() => setPhase("mode")}>
                Back
              </button>
              <button
                className="btn btn--primary"
                onClick={startLearning}
                disabled={selected.size === 0}
              >
                Start learning ({selected.size})
              </button>
            </div>
          </div>
        )}

        {/* ---- Phase: learning ---- */}
        {phase === "learning" && current && (
          <>
            <div className="learn-progress">
              <div className="learn-progress__bar">
                <span style={{ width: `${(idx / queue.length) * 100}%` }} />
              </div>
              <span className="learn-progress__label">
                Task {idx + 1} of {queue.length}: <strong>{current.title}</strong>
              </span>
            </div>
            <div className="learn-modal__body learn-chat" ref={scrollRef}>
              {thread.map((m, i) => (
                <div key={i} className={`learn-bubble learn-bubble--${m.role}`}>
                  {m.role === "assistant" ? (
                    <span dangerouslySetInnerHTML={{ __html: fmt(m.content) }} />
                  ) : (
                    m.content
                  )}
                </div>
              ))}
              {busy && <div className="learn-bubble learn-bubble--assistant">Thinking…</div>}
            </div>
            <div className="learn-modal__foot">
              <form onSubmit={send} className="learn-input-row">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={
                    mode === "interactive"
                      ? "Answer or ask a question…"
                      : "Ask a follow up…"
                  }
                  disabled={busy}
                />
                <button type="submit" className="btn btn--soft btn--sm" disabled={busy || !input.trim()}>
                  Send
                </button>
              </form>
              <button
                className="btn btn--primary btn--sm"
                onClick={markDoneNext}
                disabled={busy}
              >
                {idx + 1 >= queue.length ? "Finish" : "Mark done & next →"}
              </button>
            </div>
          </>
        )}

        {/* ---- Phase: done ---- */}
        {phase === "done" && (
          <div className="learn-modal__body learn-done">
            <span className="learn-done__mark">✓</span>
            <h3>Nice work.</h3>
            <p className="learn-lead">
              You've worked through your tasks for <strong>{stepTitle}</strong>.
              Mark this {cat} as completed?
            </p>
            <div className="learn-modal__actions">
              <button className="btn btn--ghost" onClick={onClose}>
                Not yet
              </button>
              <button className="btn btn--primary" onClick={completeStep} disabled={busy}>
                Mark {cat} complete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
