import { useEffect, useRef, useState, type FormEvent } from "react";
import { sendChat, type ChatMsg } from "../api/endpoints";

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
  const bodyRef = useRef<HTMLDivElement>(null);

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

  function startNew() {
    const s = freshSession();
    setSessions((prev) => [s, ...prev]);
    setActiveId(s.id);
    setShowList(false);
    setError(null);
  }

  function deleteSession(id: number) {
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      return next.length ? next : [freshSession()];
    });
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setError(null);
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
      const { reply, changed } = await sendChat(history);
      updateActive((s) => ({
        ...s,
        messages: [...s.messages, { role: "assistant", content: reply }],
        updated: Date.now(),
      }));
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
                    onClick={() => {
                      setActiveId(s.id);
                      setShowList(false);
                    }}
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
