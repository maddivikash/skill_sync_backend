import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { prepAnalyze, prepExtract, type PrepReport } from "../api/endpoints";
import Modal from "./Modal";
import { logActivity } from "../lib/activity";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export default function JobPrepModal({ open, onClose, onCreated }: Props) {
  const navigate = useNavigate();
  const [jd, setJd] = useState("");
  const [days, setDays] = useState(30);
  const [busy, setBusy] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [attachedName, setAttachedName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<PrepReport | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function reset() {
    setJd("");
    setReport(null);
    setError(null);
    setAttachedName(null);
  }

  async function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-picking the same file
    if (!file || extracting) return;
    setExtracting(true);
    setError(null);
    try {
      const { text } = await prepExtract(file);
      setJd(text);
      setAttachedName(file.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't read that file.");
    } finally {
      setExtracting(false);
    }
  }

  async function analyze(e: FormEvent) {
    e.preventDefault();
    if (jd.trim().length < 40 || busy) return;
    setBusy(true);
    setError(null);
    try {
      const r = await prepAnalyze(jd.trim(), days);
      setReport(r);
      logActivity("goal");
      onCreated();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Couldn't analyze that. Please try again."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      title={report ? "Your readiness report" : "Prep for a job"}
      onClose={() => {
        reset();
        onClose();
      }}
    >
      {!report ? (
        <form onSubmit={analyze} className="prep-form">
          <p className="prep-form__lead">
            Paste the job description. You'll get an honest readiness score,
            what you're missing, and a day-by-day prep plan built from it.
          </p>
          <textarea
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the full job description here…"
            rows={9}
            disabled={busy || extracting}
          />
          <div className="prep-form__attach">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp"
              onChange={handleFile}
              hidden
            />
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => fileRef.current?.click()}
              disabled={busy || extracting}
            >
              {extracting ? "Reading file…" : "📎 Attach a file (PDF, image, or TXT)"}
            </button>
            {attachedName && !extracting && (
              <span className="prep-form__attached">
                ✓ {attachedName}: review the text above, then analyze
              </span>
            )}
          </div>
          <div className="prep-form__row">
            <label className="prep-form__days">
              <span>Prep time</span>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                disabled={busy}
              >
                <option value={14}>2 weeks</option>
                <option value={30}>30 days</option>
                <option value={45}>45 days</option>
                <option value={60}>60 days</option>
              </select>
            </label>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={busy || jd.trim().length < 40}
            >
              {busy ? "Analyzing…" : "Analyze & build my plan"}
            </button>
          </div>
          {busy && (
            <p className="prep-form__building">
              <span className="learn-spinner" aria-hidden="true" /> Reading the
              JD, scoring your readiness, building the plan…
            </p>
          )}
          {error && <div className="alert alert--error">{error}</div>}
        </form>
      ) : (
        <div className="prep-report">
          <div className="prep-report__score">
            <span className="prep-report__num">{report.readiness}</span>
            <span className="prep-report__label">
              ready for <strong>{report.role}</strong> today
            </span>
          </div>
          {report.summary && <p className="prep-report__summary">{report.summary}</p>}

          {report.strengths.length > 0 && (
            <div className="prep-report__block">
              <h4>You already have</h4>
              <ul>
                {report.strengths.map((s, i) => (
                  <li key={i} className="is-strength">✓ {s}</li>
                ))}
              </ul>
            </div>
          )}
          {report.gaps.length > 0 && (
            <div className="prep-report__block">
              <h4>The plan targets</h4>
              <ul>
                {report.gaps.map((g, i) => (
                  <li key={i} className="is-gap">→ {g}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="prep-report__foot">
            {report.total_tasks} dated tasks over {days} days. Finish them and
            your readiness climbs to 100.
          </p>
          <div className="prep-report__actions">
            <button className="btn btn--ghost" onClick={() => { reset(); onClose(); }}>
              Close
            </button>
            <button
              className="btn btn--primary"
              onClick={() => {
                const id = report.goal_id;
                reset();
                onClose();
                navigate(`/goals/${id}`);
              }}
            >
              Open my plan →
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
