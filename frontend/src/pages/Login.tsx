import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 401
          ? "Invalid email or password."
          : err instanceof Error
          ? err.message
          : "Something went wrong. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page auth-page--split">
      <div className="auth-hero">
        <span className="eyebrow">Momentum for mastery</span>
        <h1 className="auth-hero__title">
          Rise to the role
          <br />
          <em>you're aiming for.</em>
        </h1>
        <p className="auth-hero__sub">
          Pick a target role: engineer, designer, UPSC, anything. Ascend turns
          it into a living plan you can actually finish.
        </p>
        <ul className="auth-hero__points">
          <li>
            <strong>Structured paths.</strong> Skills, courses, tools and
            projects, broken into steps and tasks.
          </li>
          <li>
            <strong>An AI coach.</strong> Ask what to learn next and it builds
            your plan with you.
          </li>
          <li>
            <strong>Momentum you can see.</strong> XP, levels and streaks
            reward finishing, not just planning.
          </li>
        </ul>
      </div>
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
        <h1 className="auth-title">Welcome back</h1>
        <p className="auth-subtitle">Sign in to keep your goals on track.</p>

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
          <label className="field">
            <span className="field__label">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              placeholder="••••••••"
            />
          </label>
          <button
            className="btn btn--primary btn--block"
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="auth-footer" style={{ margin: "14px 0 0" }}>
          <Link to="/forgot-password">Forgot your password?</Link>
        </p>
        <p className="auth-footer">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </div>
    </div>
  );
}
