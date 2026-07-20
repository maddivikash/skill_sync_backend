import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  createPath,
  createStep,
  listPaths,
  sendChat,
  type ChatMsg,
  type ChatSuggestion,
} from "../api/endpoints";

const PLURAL: Record<string, string> = {
  skill: "Skills",
  course: "Courses",
  tool: "Tools",
  project: "Projects",
};
const CAT_ORDER = ["skill", "course", "tool", "project"];

const STORE_KEY = "skillsync_chat_v1";
const GREETING: ChatMsg = {
  role: "assistant",
  content:
    "Hi! I'm your Ascend Coach. Ask me about skills to learn, courses to take, or how to plan a goal.",
};

interface Session {
  id: number;
  title: string;
  messages: ChatMsg[];
  updated: number;
}

// Minimal, safe markdown -> HTML (escape first, then bold/code/line breaks +
// simple bullet lines) so replies don't show raw ** or #.
function fmt(text: string): string {
  const esc = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return esc
    .replace(/^\s*#{1,6}\s*/gm, "") // drop heading hashes
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^\s*[-*]\s+/gm, "• ") // bullets -> •
    .replace(/\n/g, "<br/>");
}

function uid(): string {
  return localStorage.getItem("skillsync_uid") || "anon";
}
function readAll(): Record<string, Session[]> {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
  } catch {
    return {};
  }
}
function loadSessions(): Session[] {
  return readAll()[uid()] || [];
}
function persist(sessions: Session[]): void {
  const all = readAll();
  all[uid()] = sessions;
  localStorage.setItem(STORE_KEY, JSON.stringify(all));
}
function freshSession(): Session {
  return { id: Date.now(), title: "New chat", messages: [GREETING], updated: Date.now() };
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [sessions, setSessions] = useState<Session[]>(() => {
    const s = loadSessions();
    return s.length ? s : [freshSession()];
  });
  const [activeId, setActiveId] = useState<number>(0);
  const [showList, setShowList] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<ChatSuggestion[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [goalId, setGoalId] = useState<number | null>(null); // persistent context for the coach
  const [suggestGoalId, setSuggestGoalId] = useState<number | null>(null); // goal the CURRENT chips add to
  const [adding, setAdding] = useState(false);
  const [catIndex, setCatIndex] = useState(0);
  const bodyRef = useRef<HTMLDivElement>(null);

  const keyOf = (s: { name: string; category: string }) => `${s.category}|${s.name}`;

  const active = sessions.find((s) => s.id === activeId) ?? sessions[0];

  // Keep a valid active session selected.
  useEffect(() => {
    if (!sessions.find((s) => s.id === activeId)) {
      setActiveId(sessions[0]?.id ?? 0);
    }
  }, [sessions, activeId]);

  // Persist on every change.
  useEffect(() => {
    persist(sessions);
  }, [sessions]);

  // Push the app content left while the drawer is open.
  useEffect(() => {
    document.body.classList.toggle("coach-open", open);
    return () => document.body.classList.remove("coach-open");
  }, [open]);

  useEffect(() => {
    bodyRef.current?.scrollTo({
      top: bodyRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [active?.messages, busy, open, activeId]);

  function updateActive(fn: (s: Session) => Session) {
    setSessions((prev) => prev.map((s) => (s.id === active.id ? fn(s) : s)));
  }

  function clearChips() {
    setSuggestions([]);
    setSelected(new Set());
    setCatIndex(0);
    setSuggestGoalId(null);
  }

  // Move to the next category that has suggestions; wrap up when done.
  // NOTE: no side effects inside setState updaters — React may replay them,
  // which duplicated the wrap-up message.
  function advance() {
    const present = CAT_ORDER.filter((c) => suggestions.some((s) => s.category === c));
    setSelected(new Set());
    if (catIndex + 1 >= present.length) {
      setSuggestions([]);
      setCatIndex(0);
      updateActive((s) => ({
        ...s,
        messages: [
          ...s.messages,
          {
            role: "assistant",
            content:
              "Your goal is all set — you can see it on your dashboard and start checking things off. Anything else you'd like help with?",
          },
        ],
        updated: Date.now(),
      }));
    } else {
      setCatIndex(catIndex + 1);
    }
  }

  function startNew() {
    const s = freshSession();
    setSessions((prev) => [s, ...prev]);
    setActiveId(s.id);
    setShowList(false);
    setError(null);
    clearChips();
  }

  function switchTo(id: number) {
    setActiveId(id);
    setShowList(false);
    clearChips();
  }

  function deleteSession(id: number) {
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      return next.length ? next : [freshSession()];
    });
  }

  async function sendMessage(raw: string) {
    const text = raw.trim();
    if (!text || busy) return;
    setError(null);
    setSuggestions([]);
    setSelected(new Set());
    const userMsg: ChatMsg = { role: "user", content: text };
    const hadUser = active.messages.some((m) => m.role === "user");
    updateActive((s) => ({
      ...s,
      messages: [...s.messages, userMsg],
      title: hadUser ? s.title : text.slice(0, 40),
      updated: Date.now(),
    }));
    const history = [...active.messages, userMsg].slice(-12);
    setInput("");
    setBusy(true);
    try {
      const { reply, changed, suggestions: sug, goal_id } = await sendChat(
        history,
        goalId
      );
      updateActive((s) => ({
        ...s,
        messages: [...s.messages, { role: "assistant", content: reply }],
        updated: Date.now(),
      }));
      setSuggestions(sug ?? []);
      setCatIndex(0);
      // These chips add ONLY to the goal they belong to (null = don't offer Add).
      setSuggestGoalId(sug && sug.length ? goal_id ?? null : null);
      if (goal_id) setGoalId(goal_id); // persistent context for later requests
      // If the coach changed data (created a goal/task/etc.), refresh the app UI.
      if (changed) window.dispatchEvent(new Event("skillsync:data-changed"));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "The coach is unavailable right now."
      );
    } finally {
      setBusy(false);
    }
  }

  function handleSend(e: FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  function toggleChip(s: { name: string; category: string }) {
    setSelected((prev) => {
      const next = new Set(prev);
      const k = keyOf(s);
      next.has(k) ? next.delete(k) : next.add(k);
      return next;
    });
  }

  // Add the selected chips straight to the goal (no AI, no new goal).
  async function addSelected() {
    if (!suggestGoalId || selected.size === 0 || adding) return;
    setAdding(true);
    try {
      const chosen = suggestions.filter((s) => selected.has(keyOf(s)));
      const paths = await listPaths(suggestGoalId);
      const byCat: Record<string, ChatSuggestion[]> = {};
      chosen.forEach((s) => (byCat[s.category] ??= []).push(s));
      for (const cat of Object.keys(byCat)) {
        const title = PLURAL[cat] || "Skills";
        let path = paths.find(
          (p) => p.title.trim().toLowerCase() === title.toLowerCase()
        );
        if (!path) {
          path = await createPath(suggestGoalId, {
            title,
            description: `Suggested ${title.toLowerCase()}`,
          });
        }
        for (const item of byCat[cat]) {
          // Preserve course links/meta the same way the wizard does.
          const desc =
            item.category === "course"
              ? [
                  [item.provider, item.estimated_hours ? `~${item.estimated_hours}h` : null]
                    .filter(Boolean)
                    .join(" · "),
                  item.url,
                ]
                  .filter(Boolean)
                  .join(" · ")
              : item.description || undefined;
          await createStep(path.id, { title: item.name, description: desc || undefined });
        }
      }
      window.dispatchEvent(new Event("skillsync:data-changed"));
      updateActive((s) => ({
        ...s,
        messages: [
          ...s.messages,
          {
            role: "assistant",
            content: `Added ${chosen.length} item${chosen.length > 1 ? "s" : ""} to your goal. ✓`,
          },
        ],
        updated: Date.now(),
      }));
      advance(); // move to the next category (courses → tools → projects)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't add those.");
    } finally {
      setAdding(false);
    }
  }

  return (
    <>
      {!open && (
        <button
          className="coach-fab"
          onClick={() => setOpen(true)}
          aria-label="Open Ascend Coach"
          title="Ascend Coach"
        >
          ✦
        </button>
      )}

      {open && (
        <div className="coach" role="dialog" aria-label="Ascend Coach">
          <div className="coach__head">
            <div className="coach__head-main">
              <span className="coach__title">Ascend Coach</span>
              <span className="coach__sub">Learning &amp; courses only</span>
            </div>
            <div className="coach__head-actions">
              <button
                className="coach__icon"
                onClick={startNew}
                title="New chat"
                aria-label="New chat"
              >
                ＋
              </button>
              <button
                className={`coach__icon ${showList ? "is-active" : ""}`}
                onClick={() => setShowList((v) => !v)}
                title="Chat history"
                aria-label="Chat history"
              >
                ☰
              </button>
              <button
                className="coach__close"
                onClick={() => setOpen(false)}
                aria-label="Close coach"
              >
                ✕
              </button>
            </div>
          </div>

          {showList && (
            <div className="coach__sessions">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  className={`coach__session ${s.id === active.id ? "is-active" : ""}`}
                >
                  <button
                    className="coach__session-title"
                    onClick={() => switchTo(s.id)}
                  >
                    {s.title || "New chat"}
                  </button>
                  <button
                    className="coach__session-del"
                    onClick={() => deleteSession(s.id)}
                    aria-label="Delete chat"
                    title="Delete chat"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="coach__body" ref={bodyRef}>
            {active.messages.map((m, i) => (
              <div
                key={i}
                className={`coach__msg coach__msg--${m.role}`}
                dangerouslySetInnerHTML={{ __html: fmt(m.content) }}
              />
            ))}
            {busy && (
              <div className="coach__msg coach__msg--assistant coach__msg--typing">
                Thinking…
              </div>
            )}
            {!busy &&
              suggestions.length > 0 &&
              (() => {
                const present = CAT_ORDER.filter((c) =>
                  suggestions.some((s) => s.category === c)
                );
                const cat = present[catIndex];
                if (!cat) return null;
                const chips = suggestions.filter((s) => s.category === cat);
                return (
                  <div className="coach__suggest">
                    <div className="coach__suggest-head">
                      <span>{PLURAL[cat]} — pick what fits</span>
                      <span className="coach__suggest-step">
                        {catIndex + 1}/{present.length}
                      </span>
                    </div>
                    <div className="coach__chips">
                      {chips.map((sg, i) => {
                        const on = selected.has(keyOf(sg));
                        return (
                          <button
                            key={i}
                            className={`coach__chip ${on ? "is-selected" : ""}`}
                            onClick={() => toggleChip(sg)}
                          >
                            {on ? "✓ " : "+ "}
                            {sg.name}
                          </button>
                        );
                      })}
                    </div>
                    <div className="coach__suggest-actions">
                      {suggestGoalId && selected.size > 0 && (
                        <button
                          className="btn btn--primary btn--sm"
                          onClick={addSelected}
                          disabled={adding}
                        >
                          {adding ? "Adding…" : `Add ${selected.size}`}
                        </button>
                      )}
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={advance}
                        disabled={adding}
                      >
                        {catIndex + 1 < present.length ? "Skip →" : "Done"}
                      </button>
                    </div>
                  </div>
                );
              })()}
            {error && <div className="coach__error">{error}</div>}
          </div>

          <form className="coach__input" onSubmit={handleSend}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a skill or course…"
              disabled={busy}
              autoFocus
            />
            <button
              className="btn btn--primary btn--sm"
              type="submit"
              disabled={busy || !input.trim()}
            >
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}
