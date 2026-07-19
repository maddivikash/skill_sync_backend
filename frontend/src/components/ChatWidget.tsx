import { useEffect, useRef, useState, type FormEvent } from "react";
import { sendChat, type ChatMsg } from "../api/endpoints";

const GREETING: ChatMsg = {
  role: "assistant",
  content:
    "Hi! I'm your SkillSync Coach. Ask me about skills to learn, courses to take, or how to plan a goal.",
};

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([GREETING]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy, open]);

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setError(null);
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      // Send only real turns (skip the local greeting).
      const history = next.filter((m) => m !== GREETING);
      const { reply } = await sendChat(history);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
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
      <button
        className="coach-fab"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close coach" : "Open SkillSync Coach"}
        title="SkillSync Coach"
      >
        {open ? "✕" : "✦"}
      </button>

      {open && (
        <div className="coach" role="dialog" aria-label="SkillSync Coach">
          <div className="coach__head">
            <span className="coach__title">SkillSync Coach</span>
            <span className="coach__sub">Learning &amp; courses only</span>
          </div>

          <div className="coach__body" ref={bodyRef}>
            {messages.map((m, i) => (
              <div key={i} className={`coach__msg coach__msg--${m.role}`}>
                {m.content}
              </div>
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
