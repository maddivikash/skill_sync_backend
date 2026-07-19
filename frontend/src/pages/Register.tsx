import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register as apiRegister } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export default function Register() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setSubmitting(true);
    try {
      await apiRegister({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
      });
      // Auto-login after successful registration.
      try {
        await login(email.trim(), password);
        navigate("/", { replace: true });
      } catch {
        navigate("/login", { replace: true });
      }
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 400
          ? "An account with that email already exists."
          : err instanceof Error
          ? err.message
          : "Something went wrong. Please try again.";
      setError(msg);
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
        <h1 className="auth-title">Create your account</h1>
        <p className="auth-subtitle">Turn your career goals into a plan.</p>

        {error && <div className="alert alert--error">{error}</div>}

        <form onSubmit={handleSubmit} className="form">
          <label className="field">
            <span className="field__label">Full name</span>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              autoComplete="name"
              placeholder="Ada Lovelace"
            />
          </label>
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
              minLength={6}
              autoComplete="new-password"
              placeholder="At least 6 characters"
            />
            <span className="field__hint">Minimum 6 characters.</span>
          </label>
          <button
            className="btn btn--primary btn--block"
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
