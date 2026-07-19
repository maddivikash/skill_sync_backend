import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { confirmPasswordReset } from "../api/endpoints";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setSubmitting(true);
    try {
      await confirmPasswordReset(token, password);
      setDone(true);
      setTimeout(() => navigate("/login", { replace: true }), 1600);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Couldn't reset your password."
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
            As<span className="brand__accent">cend</span>
          </span>
        </div>

        <h1 className="auth-title">Set a new password</h1>

        {!token ? (
          <>
            <p className="auth-subtitle">
              This reset link is missing or invalid. Request a new one.
            </p>
            <Link className="btn btn--primary btn--block" to="/forgot-password">
              Request a reset link
            </Link>
          </>
        ) : done ? (
          <>
            <p className="auth-subtitle">
              Your password has been reset. Taking you to sign in…
            </p>
            <Link className="btn btn--primary btn--block" to="/login">
              Sign in now
            </Link>
          </>
        ) : (
          <>
            <p className="auth-subtitle">Choose a new password for your account.</p>
            {error && <div className="alert alert--error">{error}</div>}
            <form onSubmit={handleSubmit} className="form">
              <label className="field">
                <span className="field__label">New password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  placeholder="••••••••"
                />
              </label>
              <label className="field">
                <span className="field__label">Confirm new password</span>
                <input
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                  autoComplete="new-password"
                  placeholder="••••••••"
                />
              </label>
              <button
                className="btn btn--primary btn--block"
                type="submit"
                disabled={submitting}
              >
                {submitting ? "Resetting…" : "Reset password"}
              </button>
            </form>
            <p className="auth-footer">
              <Link to="/login">Back to sign in</Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
