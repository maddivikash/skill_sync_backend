export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const ACCESS_KEY = "skillsync_access_token";
const REFRESH_KEY = "skillsync_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function setTokens(access: string, refresh?: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function onUnauthorized(): void {
  clearTokens();
  // Avoid redirect loop if we are already on an auth page.
  const path = window.location.pathname;
  if (path !== "/login" && path !== "/register") {
    window.location.assign("/login");
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
      return data.detail.map((d: { msg: string }) => d.msg).join(", ");
    }
    if (data?.message) return String(data.message);
  } catch {
    /* not JSON */
  }
  return res.statusText || `Request failed (${res.status})`;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  /** Send as application/x-www-form-urlencoded instead of JSON. */
  form?: Record<string, string>;
  /** Skip attaching the Bearer token (used for auth endpoints). */
  auth?: boolean;
  /** Internal: set after we transparently refreshed + retried once. */
  _retried?: boolean;
}

// Silently exchange the refresh token for a new access token. Deduped so
// concurrent 401s trigger only one refresh call.
let refreshInFlight: Promise<boolean> | null = null;
function refreshAccessToken(): Promise<boolean> {
  const rt = localStorage.getItem(REFRESH_KEY);
  if (!rt) return Promise.resolve(false);
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(
          `${API_URL}/api/refresh?refresh_token=${encodeURIComponent(rt)}`,
          { method: "POST" }
        );
        if (!res.ok) return false;
        const data = await res.json();
        if (data?.access_token) {
          localStorage.setItem(ACCESS_KEY, data.access_token);
          return true;
        }
        return false;
      } catch {
        return false;
      }
    })();
    refreshInFlight.finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

/**
 * Core fetch wrapper: attaches Bearer token, sets content-type,
 * handles 401 by clearing tokens + redirecting to /login,
 * and parses JSON (or returns undefined for 204).
 */
export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, form, auth = true, _retried = false } = options;

  const headers: Record<string, string> = {};
  let payload: BodyInit | undefined;

  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form).toString();
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  if (auth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: payload,
  });

  if (res.status === 401) {
    // Access token likely expired: try a silent refresh, then retry once.
    if (auth && !_retried) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        return apiFetch<T>(path, { ...options, _retried: true });
      }
    }
    onUnauthorized();
    throw new ApiError("Your session has expired. Please sign in again.", 401);
  }

  if (!res.ok) {
    throw new ApiError(await parseError(res), res.status);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
