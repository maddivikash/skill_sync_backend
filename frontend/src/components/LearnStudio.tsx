import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  learnPlan,
  learnReplan,
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

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// Lightweight, language-agnostic syntax highlighting for chat code blocks.
// One alternation pass so tokens never overlap: comments, strings, preprocessor
// or Python-style # lines, numbers, keywords.
const CODE_KEYWORDS = new Set([
  // shared / c-family
  "if", "else", "for", "while", "do", "switch", "case", "default", "break",
  "continue", "return", "class", "struct", "enum", "public", "private",
  "protected", "static", "const", "void", "int", "double", "float", "bool",
  "char", "long", "short", "unsigned", "signed", "auto", "new", "delete",
  "try", "catch", "throw", "namespace", "using", "template", "typename",
  "virtual", "override", "true", "false", "nullptr", "this",
  // js / ts
  "function", "let", "var", "await", "async", "import", "export", "from",
  "extends", "implements", "interface", "type", "null", "undefined", "of",
  // python
  "def", "elif", "lambda", "pass", "raise", "with", "as", "in", "not", "and",
  "or", "is", "None", "True", "False", "print", "self", "yield", "global",
  // sql-ish
  "select", "insert", "update", "where", "join", "group", "order", "by",
]);

function highlightCode(code: string): string {
  const esc = escapeHtml(code);
  const token =
    /(\/\/[^\n]*|\/\*[\s\S]*?\*\/)|(#[^\n]*)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)|\b(\d+(?:\.\d+)?[fLu]*)\b|\b([A-Za-z_][A-Za-z0-9_]*)\b/g;
  return esc.replace(token, (m, comment, meta, str, num, word) => {
    if (comment) return `<span class="tok-comment">${m}</span>`;
    if (meta) return `<span class="tok-meta">${m}</span>`;
    if (str) return `<span class="tok-string">${m}</span>`;
    if (num) return `<span class="tok-number">${m}</span>`;
    if (word && CODE_KEYWORDS.has(word)) return `<span class="tok-keyword">${m}</span>`;
    return m;
  });
}

// Minimal, safe markdown -> HTML. Fenced ```code``` blocks are lifted out
// first (rendered dark with syntax colors), then the rest gets escape +
// bold/inline-code/bullets/breaks.
function fmt(text: string): string {
  const blocks: string[] = [];
  const withPlaceholders = text.replace(
    /```[\w+#-]*[ \t]*\n?([\s\S]*?)```/g,
    (_m, code: string) => {
      blocks.push(
        `<pre class="learn-code"><code>${highlightCode(code.replace(/\n$/, ""))}</code></pre>`
      );
      return `\u0000${blocks.length - 1}\u0000`;
    }
  );
  const html = escapeHtml(withPlaceholders)
    .replace(/^\s*#{1,6}\s*/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^\s*[-*]\s+/gm, "• ")
    .replace(/\n/g, "<br/>");
  // Re-insert code blocks, dropping any <br/> hugging the placeholder so the
  // block doesn't get extra blank lines around it.
  return html.replace(
    /(?:<br\/>)?\u0000(\d+)\u0000(?:<br\/>)?/g,
    (_m, i: string) => blocks[Number(i)]
  );
}

interface Props {
  stepId: number;
  stepTitle: string;
  /** Jump straight to this task's saved chat thread on open (revisit mode). */
  initialTaskId?: number;
  onChanged: () => void;
  onClose: () => void;
}

type Phase = "mode" | "tasks" | "learning" | "done";

// Persist a learn session per step so reopening resumes the same chat.
interface SavedSession {
  mode: LearnMode;
  phase: Phase;
  idx: number;
  queueIds: number[];
  threads: Record<number, ChatMsg[]>;
}
const savedKey = (stepId: number) => `skillsync_learn_${stepId}`;
function loadSaved(stepId: number): SavedSession | null {
  try {
    const raw = localStorage.getItem(savedKey(stepId));
    return raw ? (JSON.parse(raw) as SavedSession) : null;
  } catch {
    return null;
  }
}

/** Task ids in this step that already have a coach chat thread saved, so the
    task list can offer "revisit chat" on started/completed tasks. */
export function savedChatTaskIds(stepId: number): Set<number> {
  const saved = loadSaved(stepId);
  const ids = new Set<number>();
  if (saved?.threads) {
    for (const [id, msgs] of Object.entries(saved.threads)) {
      if (Array.isArray(msgs) && msgs.length > 0) ids.add(Number(id));
    }
  }
  return ids;
}

export default function LearnStudio({
  stepId,
  stepTitle,
  initialTaskId,
  onChanged,
  onClose,
}: Props) {
  const { error } = useToast();
  const saved = useRef<SavedSession | null>(loadSaved(stepId)).current;
  const [phase, setPhase] = useState<Phase>("mode");
  const [mode, setMode] = useState<LearnMode>(saved?.mode ?? "guided");
  const [plan, setPlan] = useState<LearnPlan | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [queue, setQueue] = useState<LearnTask[]>([]);
  const [idx, setIdx] = useState(0);
  const [threads, setThreads] = useState<Record<number, ChatMsg[]>>(
    saved?.threads ?? {}
  );
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [resuming, setResuming] = useState(!!saved);
  const [refine, setRefine] = useState("");
  const [refining, setRefining] = useState(false);
  const [refineNote, setRefineNote] = useState<string | null>(null);
  const kicked = useRef<Set<number>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  // Resume a saved session: reload the plan, rebuild the queue, jump back in.
  useEffect(() => {
    if (!saved) return;
    let cancelled = false;
    (async () => {
      try {
        const p = await learnPlan(stepId);
        if (cancelled) return;
        setPlan(p);
        const byId = new Map(p.tasks.map((t) => [t.id, t]));
        const q = (saved.queueIds || [])
          .map((id) => byId.get(id))
          .filter(Boolean) as LearnTask[];
        const queue = q.length ? q : p.tasks;
        setQueue(queue);
        Object.keys(saved.threads || {}).forEach((id) =>
          kicked.current.add(Number(id))
        );
        // Revisit mode: land directly on the requested task's thread.
        const jumpTo =
          initialTaskId != null
            ? queue.findIndex((t) => t.id === initialTaskId)
            : -1;
        if (jumpTo >= 0) {
          setIdx(jumpTo);
          setPhase("learning");
        } else {
          setIdx(Math.min(saved.idx ?? 0, Math.max(0, queue.length - 1)));
          setPhase(saved.phase === "done" ? "done" : "learning");
        }
      } catch {
        setResuming(false); // fall back to the mode screen
      } finally {
        if (!cancelled) setResuming(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const current = queue[idx];
  const thread = current ? threads[current.id] ?? [] : [];

  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && handleClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [thread, busy, phase]);

  // Persist the active session so reopening this step resumes the same chat.
  useEffect(() => {
    if (phase !== "learning" && phase !== "done") return;
    try {
      const payload: SavedSession = {
        mode,
        phase,
        idx,
        queueIds: queue.map((t) => t.id),
        threads,
      };
      localStorage.setItem(savedKey(stepId), JSON.stringify(payload));
    } catch {
      /* ignore quota errors */
    }
  }, [phase, idx, queue, threads, mode, stepId]);

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

  // Free-flow: reshape the plan from a typed instruction, keep it structured.
  async function handleRefine(e: FormEvent) {
    e.preventDefault();
    const instruction = refine.trim();
    if (!instruction || refining) return;
    setRefining(true);
    setRefineNote(null);
    try {
      const p = await learnReplan(stepId, instruction);
      setPlan(p);
      setSelected(new Set(p.tasks.filter((t) => !t.is_done).map((t) => t.id)));
      setRefine("");
      setRefineNote("Updated the plan below.");
    } catch (err) {
      setRefineNote(
        err instanceof Error ? err.message : "Couldn't update the plan."
      );
    } finally {
      setRefining(false);
    }
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

  // Typing "next" / "done" / "move on" advances the flow through chat, no button.
  const ADVANCE_RE =
    /^(next|next topic|done|mark (it )?done|complete|move on|got it,?\s*next|continue)\.?$/i;

  async function send(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy || !current) return;
    if (ADVANCE_RE.test(text)) {
      setInput("");
      markDoneNext();
      return;
    }
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
        // Reflect locally; do NOT refresh the parent here (that remounts and
        // closes the modal). The parent refreshes once when the modal closes.
        setQueue((q) =>
          q.map((t) => (t.id === current.id ? { ...t, is_done: true } : t))
        );
      }
      if (idx + 1 >= queue.length) setPhase("done");
      else setIdx((i) => i + 1);
    } catch (err) {
      error(err instanceof Error ? err.message : "Couldn't save progress.");
    } finally {
      setBusy(false);
    }
  }

  // Refresh the underlying goal/dashboard once, then close.
  function handleClose() {
    onChanged();
    window.dispatchEvent(new Event("skillsync:data-changed"));
    onClose();
  }

  async function completeStep() {
    setBusy(true);
    try {
      await updateStep(stepId, { is_done: true });
      logActivity("complete_step");
      // Keep the saved session: completed tasks stay revisitable from the
      // task list ("revisit chat"), so learners can revise old threads.
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
    <div
      className="learn-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
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
          <button className="icon-btn" onClick={handleClose} aria-label="Close">
            ×
          </button>
        </header>

        {/* ---- Resuming a saved session ---- */}
        {phase === "mode" && resuming && (
          <div className="learn-modal__body">
            <p className="learn-lead">Picking up where you left off…</p>
          </div>
        )}

        {/* ---- Phase: choose a mode ---- */}
        {phase === "mode" && !resuming && (
          <div className="learn-modal__body learn-modes">
            <div className="learn-modes__intro">
              <h3 className="learn-modes__title">
                How would you like to learn <em>{stepTitle}</em>?
              </h3>
              <p className="learn-lead">
                Pick a style and the coach builds a task plan, then walks you
                through it one step at a time.
              </p>
            </div>

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
                <span className="learn-mode-card__cta">Start guided →</span>
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
                <span className="learn-mode-card__cta">Start interactive →</span>
              </button>
            </div>

            {planning ? (
              <p className="learn-modes__building">
                <span className="learn-spinner" aria-hidden="true" /> Building
                your task list…
              </p>
            ) : (
              <ol className="learn-steps" aria-label="How it works">
                <li><span>1</span> Pick a style</li>
                <li><span>2</span> Coach builds your tasks</li>
                <li><span>3</span> Learn one task at a time</li>
                <li><span>4</span> Mark it complete</li>
              </ol>
            )}
          </div>
        )}

        {/* ---- Phase: pick tasks (structured, but shapeable by chat) ---- */}
        {phase === "tasks" && plan && (
          <div className="learn-modal__body">
            <p className="learn-lead">
              Here's a plan for <strong>{stepTitle}</strong>. Pick what you want
              to work through, or tell me how to change it.
            </p>
            <ul className={`learn-task-picker ${refining ? "is-refining" : ""}`}>
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

            {/* free-flow refinement: quick chips + type your own */}
            <div className="learn-refine">
              <div className="learn-refine__chips">
                {[
                  "Regenerate the plan",
                  "Make it shorter",
                  "Add a hands-on project",
                  "Go more advanced",
                ].map((q) => (
                  <button
                    key={q}
                    className="learn-refine__chip"
                    disabled={refining}
                    onClick={() => {
                      setRefine(q);
                      handleRefine({ preventDefault() {} } as FormEvent);
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
              <form onSubmit={handleRefine} className="learn-refine__row">
                <input
                  value={refine}
                  onChange={(e) => setRefine(e.target.value)}
                  placeholder="e.g. add a topic on jet engines, focus on exams…"
                  disabled={refining}
                />
                <button
                  type="submit"
                  className="btn btn--soft btn--sm"
                  disabled={refining || !refine.trim()}
                >
                  {refining ? "Updating…" : "Update plan"}
                </button>
              </form>
              {refineNote && <p className="learn-refine__note">{refineNote}</p>}
            </div>

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
              <div className="learn-progress__row">
                <span className="learn-progress__label">
                  Task {idx + 1} of {queue.length}:{" "}
                  <strong>{current.title}</strong>
                </span>
                <div className="learn-progress__nav">
                  {idx > 0 && (
                    <button
                      className="learn-next-btn"
                      onClick={() => setIdx((i) => Math.max(0, i - 1))}
                      disabled={busy}
                    >
                      ← Prev
                    </button>
                  )}
                  <button
                    className="learn-next-btn"
                    onClick={markDoneNext}
                    disabled={busy}
                  >
                    {idx + 1 >= queue.length ? "Finish →" : "Next task →"}
                  </button>
                </div>
              </div>
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
                      ? "Answer, ask a question, or type “next”…"
                      : "Ask a follow up, or type “next”…"
                  }
                  disabled={busy}
                />
                <button type="submit" className="btn btn--soft btn--sm" disabled={busy || !input.trim()}>
                  Send
                </button>
              </form>
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
              <button className="btn btn--ghost" onClick={handleClose}>
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
