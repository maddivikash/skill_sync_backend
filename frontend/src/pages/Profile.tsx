import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { changePassword, resetProgress } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/theme";
import { useConfirm, useToast } from "../context/ui";
import { resetActivity } from "../lib/activity";

export default function Profile() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const confirm = useConfirm();
  const { success, error } = useToast();
  const navigate = useNavigate();

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [savingPw, setSavingPw] = useState(false);
  const [resetting, setResetting] = useState(false);

  const initials = user?.full_name
    ? user.full_name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase()
    : "?";

  async function handleChangePassword(e: FormEvent) {
    e.preventDefault();
    if (next.length < 6) {
      error("New password must be at least 6 characters.");
      return;
    }
    if (next !== confirmPw) {
      error("New passwords do not match.");
      return;
    }
    setSavingPw(true);
    try {
      await changePassword(current, next);
      success("Password updated");
      setCurrent("");
      setNext("");
      setConfirmPw("");
    } catch (err) {
      error(err instanceof Error ? err.message : "Failed to change password.");
    } finally {
      setSavingPw(false);
    }
  }

  async function handleReset() {
    const ok = await confirm({
      title: "Reset all progress?",
      message:
        "This permanently deletes ALL your goals, learning paths, steps, tasks, and your XP / streak history. This cannot be undone.",
      confirmText: "Yes, delete everything",
      cancelText: "Keep my data",
      danger: true,
    });
    if (!ok) return;
    setResetting(true);
    try {
      await resetProgress();
      resetActivity();
      success("All progress has been reset.");
      navigate("/", { replace: true });
    } catch (err) {
      error(err instanceof Error ? err.message : "Failed to reset progress.");
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="page profile">
      <Link to="/" className="back-link">
        ← Back to dashboard
      </Link>

      <div className="page__head">
        <div>
          <h1 className="page__title">Profile &amp; settings</h1>
          <p className="page__subtitle">Manage your account and preferences.</p>
        </div>
      </div>

      {/* Account */}
      <section className="settings-card">
        <div className="settings-card__profile">
          <span className="user-chip__avatar user-chip__avatar--lg" aria-hidden="true">
            {initials}
          </span>
          <div>
            <div className="settings-card__name">{user?.full_name}</div>
            <div className="muted-note">{user?.email}</div>
          </div>
        </div>
      </section>

      {/* Preferences */}
      <section className="settings-card">
        <h2 className="settings-card__title">Preferences</h2>
        <div className="settings-row">
          <div>
            <div className="settings-row__label">Appearance</div>
            <div className="muted-note">Choose light or dark mode.</div>
          </div>
          <div className="theme-choice">
            <button
              className={`theme-choice__btn ${theme === "light" ? "is-active" : ""}`}
              onClick={() => setTheme("light")}
            >
              ☀️ Light
            </button>
            <button
              className={`theme-choice__btn ${theme === "dark" ? "is-active" : ""}`}
              onClick={() => setTheme("dark")}
            >
              🌙 Dark
            </button>
          </div>
        </div>
      </section>

      {/* Change password */}
      <section className="settings-card">
        <h2 className="settings-card__title">Change password</h2>
        <form onSubmit={handleChangePassword} className="form settings-form">
          <label className="field">
            <span className="field__label">Current password</span>
            <input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          <div className="field-row">
            <label className="field field--grow">
              <span className="field__label">New password</span>
              <input
                type="password"
                value={next}
                onChange={(e) => setNext(e.target.value)}
                required
                autoComplete="new-password"
              />
            </label>
            <label className="field field--grow">
              <span className="field__label">Confirm new password</span>
              <input
                type="password"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                required
                autoComplete="new-password"
              />
            </label>
          </div>
          <div className="form__actions">
            <button type="submit" className="btn btn--primary" disabled={savingPw}>
              {savingPw ? "Updating…" : "Update password"}
            </button>
          </div>
        </form>
      </section>

      {/* Danger zone */}
      <section className="settings-card settings-card--danger">
        <h2 className="settings-card__title">Danger zone</h2>
        <div className="settings-row">
          <div>
            <div className="settings-row__label">Reset all progress</div>
            <div className="muted-note">
              Deletes every goal, path, step, task, and your XP / streak. This
              cannot be undone.
            </div>
          </div>
          <button
            className="btn btn--danger"
            onClick={handleReset}
            disabled={resetting}
          >
            {resetting ? "Resetting…" : "Reset everything"}
          </button>
        </div>
      </section>
    </div>
  );
}
