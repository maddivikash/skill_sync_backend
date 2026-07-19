import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { requestPasswordReset } from "../api/endpoints";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await requestPasswordReset(email.trim());
      setSent(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="brand__mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
              <path
                d="M4 13l4 4L20 5"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span className="brand__name">
            Skill<span className="brand__accent">Sync</span>
          </span>
        </div>

        <h1 className="auth-title">Reset your password</h1>

        {sent ? (
          <>
            <p className="auth-subtitle">
              If an account exists for <strong>{email}</strong>, a reset link is
              on its way. Check your inbox (and spam).
            </p>
            <Link className="btn btn--primary btn--block" to="/login">
              Back to sign in
            </Link>
          </>
        ) : (
          <>
            <p className="auth-subtitle">
              Enter your email and we'll send you a link to set a new password.
            </p>
            {error && <div className="alert alert--error">{error}</div>}
            <form onSubmit={handleSubmit} className="form">
              <label className="field">
                <span className="field__label">Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  placeholder="you@example.com"
                />
              </label>
              <button
                className="btn btn--primary btn--block"
                type="submit"
                disabled={submitting}
              >
                {submitting ? "Sending…" : "Send reset link"}
              </button>
            </form>
            <p className="auth-footer">
              Remembered it? <Link to="/login">Back to sign in</Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
