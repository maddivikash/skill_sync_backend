import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  changePassword,
  getMe,
  listArchivedGoals,
  resetProgress,
  setGoalArchived,
  updatePreferences,
} from "../api/endpoints";
import type { Goal } from "../types";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/theme";
import { useConfirm, useToast } from "../context/ui";
import { resetActivity } from "../lib/activity";
import Modal from "../components/Modal";

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
  const [pwOpen, setPwOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [archived, setArchived] = useState<Goal[]>([]);
  const [unarchivingId, setUnarchivingId] = useState<number | null>(null);
  const [emailReminders, setEmailReminders] = useState(true);
  const [savingPrefs, setSavingPrefs] = useState(false);

  useEffect(() => {
    listArchivedGoals()
      .then(setArchived)
      .catch(() => setArchived([]));
    getMe()
      .then((u) => setEmailReminders(u.email_reminders ?? true))
      .catch(() => {});
  }, []);

  async function toggleEmailReminders() {
    const next = !emailReminders;
    setSavingPrefs(true);
    try {
      await updatePreferences(next);
      setEmailReminders(next);
      success(next ? "Daily email reminders on." : "Daily email reminders off.");
    } catch (err) {
      error(err instanceof Error ? err.message : "Couldn't save that.");
    } finally {
      setSavingPrefs(false);
    }
  }

  async function handleUnarchive(id: number, roleName: string) {
    setUnarchivingId(id);
    try {
      await setGoalArchived(id, false);
      setArchived((prev) => prev.filter((g) => g.id !== id));
      success(`"${roleName}" is back on your dashboard.`);
    } catch (err) {
      error(err instanceof Error ? err.message : "Failed to unarchive goal.");
    } finally {
      setUnarchivingId(null);
    }
  }

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
      setPwOpen(false);
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
            <div className="settings-row__label">Daily email reminders</div>
            <div className="muted-note">
              One morning email with your due and overdue items. On by default.
            </div>
          </div>
          <button
            className={`theme-choice__btn ${emailReminders ? "is-active" : ""}`}
            onClick={toggleEmailReminders}
            disabled={savingPrefs}
          >
            {emailReminders ? "✓ On" : "Off"}
          </button>
        </div>
        <div className="settings-row" style={{ marginTop: 16 }}>
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

      {/* Security */}
      <section className="settings-card">
        <h2 className="settings-card__title">Security</h2>
        <div className="settings-row">
          <div>
            <div className="settings-row__label">Password</div>
            <div className="muted-note">Change the password you sign in with.</div>
          </div>
          <button className="btn btn--soft" onClick={() => setPwOpen(true)}>
            Change password
          </button>
        </div>
      </section>

      <Modal open={pwOpen} title="Change password" onClose={() => setPwOpen(false)}>
        <form onSubmit={handleChangePassword} className="form settings-form">
          <label className="field">
            <span className="field__label">Current password</span>
            <input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
              autoComplete="current-password"
              autoFocus
            />
          </label>
          <label className="field">
            <span className="field__label">New password</span>
            <input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              autoComplete="new-password"
            />
          </label>
          <label className="field">
            <span className="field__label">Confirm new password</span>
            <input
              type="password"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              required
              autoComplete="new-password"
            />
          </label>
          <div className="form__actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setPwOpen(false)}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn--primary" disabled={savingPw}>
              {savingPw ? "Updating…" : "Update password"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Archived goals */}
      <section className="settings-card">
        <h2 className="settings-card__title">Archived goals</h2>
        {archived.length === 0 ? (
          <p className="muted-note">
            No archived goals. Archive a goal from its menu on the dashboard to
            tuck it away without deleting it.
          </p>
        ) : (
          <ul className="archived-list">
            {archived.map((g) => (
              <li key={g.id} className="archived-item">
                <div>
                  <div className="settings-row__label">{g.role}</div>
                  <div className="muted-note">
                    {g.hours_per_week} hrs/week · {g.duration_weeks} weeks
                  </div>
                </div>
                <button
                  className="btn btn--soft btn--sm"
                  onClick={() => handleUnarchive(g.id, g.role)}
                  disabled={unarchivingId === g.id}
                >
                  {unarchivingId === g.id ? "Restoring…" : "Unarchive"}
                </button>
              </li>
            ))}
          </ul>
        )}
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
