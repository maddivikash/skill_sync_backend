/* ============================================================
   Client-side gamification: daily-login XP + activity heatmap.
   Persisted in localStorage, keyed per user. No backend needed.
   ============================================================ */

const STORE_KEY = "skillsync_activity_v1";
const UID_KEY = "skillsync_uid";

export type ActivityKind =
  | "login"
  | "goal"
  | "path"
  | "project"
  | "step"
  | "task"
  | "complete_task"
  | "complete_step";

const XP: Record<ActivityKind, number> = {
  login: 15,
  goal: 25,
  path: 15,
  project: 20,
  step: 10,
  task: 8,
  complete_task: 5,
  complete_step: 10,
};

interface UserActivity {
  xp: number;
  days: Record<string, number>; // "YYYY-MM-DD" -> activity count
  details?: Record<string, Partial<Record<ActivityKind, number>>>; // per-day breakdown
  lastLogin: string | null;
}

/** Human labels for each activity kind (used in the heatmap tooltip). */
export const KIND_LABEL: Record<ActivityKind, string> = {
  login: "daily login",
  goal: "goal created",
  path: "path added",
  project: "project added",
  step: "step added",
  task: "task added",
  complete_task: "task completed",
  complete_step: "step completed",
};

type Store = Record<string, UserActivity>;

// ---- date helpers (local time) ----
export function dayKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function today(): string {
  return dayKey(new Date());
}

// ---- current user pointer ----
export function setCurrentUser(id: number | string): void {
  localStorage.setItem(UID_KEY, String(id));
}
export function clearCurrentUser(): void {
  localStorage.removeItem(UID_KEY);
}
function currentUid(): string | null {
  return localStorage.getItem(UID_KEY);
}

// ---- storage ----
function readStore(): Store {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    return raw ? (JSON.parse(raw) as Store) : {};
  } catch {
    return {};
  }
}
function writeStore(store: Store): void {
  localStorage.setItem(STORE_KEY, JSON.stringify(store));
}
function ensureUser(store: Store, uid: string): UserActivity {
  if (!store[uid]) {
    store[uid] = { xp: 0, days: {}, details: {}, lastLogin: null };
  }
  if (!store[uid].details) store[uid].details = {}; // migrate older records
  return store[uid];
}

/** Increment the per-day breakdown bucket for a kind. */
function bumpDetail(u: UserActivity, day: string, kind: ActivityKind): void {
  const details = u.details!;
  const bucket = (details[day] ??= {});
  bucket[kind] = (bucket[kind] ?? 0) + 1;
}

// Notify listeners (the sidebar) when activity changes.
const EVENT = "skillsync:activity";
function emit(): void {
  window.dispatchEvent(new Event(EVENT));
}
export function onActivityChange(cb: () => void): () => void {
  window.addEventListener(EVENT, cb);
  return () => window.removeEventListener(EVENT, cb);
}

/** Record an activity for the current user; awards XP and marks today active. */
export function logActivity(kind: ActivityKind): void {
  const uid = currentUid();
  if (!uid) return;
  const store = readStore();
  const u = ensureUser(store, uid);
  const t = today();
  u.xp += XP[kind];
  u.days[t] = (u.days[t] ?? 0) + 1;
  bumpDetail(u, t, kind);
  writeStore(store);
  emit();
}

/** Award the once-per-day login bonus (idempotent within a day). */
export function recordDailyLogin(): void {
  const uid = currentUid();
  if (!uid) return;
  const store = readStore();
  const u = ensureUser(store, uid);
  const t = today();
  if (u.lastLogin === t) return; // already counted today
  u.lastLogin = t;
  u.xp += XP.login;
  u.days[t] = (u.days[t] ?? 0) + 1;
  bumpDetail(u, t, "login");
  writeStore(store);
  emit();
}

/** Wipe the current user's XP / streak / activity history. */
export function resetActivity(): void {
  const uid = currentUid();
  if (!uid) return;
  const store = readStore();
  store[uid] = { xp: 0, days: {}, details: {}, lastLogin: null };
  writeStore(store);
  emit();
}

// ---- leveling ----
/** XP required to advance FROM the given level to the next. */
function costForLevel(level: number): number {
  return 100 + (level - 1) * 50;
}

export interface LevelInfo {
  level: number;
  intoLevel: number; // XP earned within the current level
  levelSpan: number; // XP needed to finish the current level
  percent: number;
}

export function levelFromXp(xp: number): LevelInfo {
  let level = 1;
  let remaining = xp;
  while (remaining >= costForLevel(level)) {
    remaining -= costForLevel(level);
    level += 1;
  }
  const span = costForLevel(level);
  return {
    level,
    intoLevel: remaining,
    levelSpan: span,
    percent: Math.round((remaining / span) * 100),
  };
}

// ---- streak ----
/** Consecutive active days ending today (or yesterday, still "alive"). */
export function currentStreak(days: Record<string, number>): number {
  const cursor = new Date();
  // If today has no activity yet, allow the streak to be anchored at yesterday.
  if (!days[dayKey(cursor)]) {
    cursor.setDate(cursor.getDate() - 1);
    if (!days[dayKey(cursor)]) return 0;
  }
  let streak = 0;
  while (days[dayKey(cursor)]) {
    streak += 1;
    cursor.setDate(cursor.getDate() - 1);
  }
  return streak;
}

// ---- summary for the UI ----
export interface ActivitySummary {
  xp: number;
  level: LevelInfo;
  streak: number;
  activeDays: number;
  days: Record<string, number>;
  details: Record<string, Partial<Record<ActivityKind, number>>>;
  todayActive: boolean;
}

export function getSummary(): ActivitySummary {
  const uid = currentUid();
  const store = readStore();
  const u = uid ? store[uid] : undefined;
  const days = u?.days ?? {};
  const xp = u?.xp ?? 0;
  return {
    xp,
    level: levelFromXp(xp),
    streak: currentStreak(days),
    activeDays: Object.keys(days).filter((d) => days[d] > 0).length,
    days,
    details: u?.details ?? {},
    todayActive: (days[today()] ?? 0) > 0,
  };
}
