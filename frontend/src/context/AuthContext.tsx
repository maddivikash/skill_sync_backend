import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { clearTokens, getAccessToken } from "../api/client";
import { getMe, login as apiLogin } from "../api/endpoints";
import {
  clearCurrentUser,
  recordDailyLogin,
  setCurrentUser,
} from "../lib/activity";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      return;
    }
    try {
      const me = await getMe();
      setUser(me);
      setCurrentUser(me.id);
      recordDailyLogin();
    } catch {
      // Token invalid/expired — clear silently.
      clearTokens();
      setUser(null);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    (async () => {
      await refreshUser();
      if (mounted) setLoading(false);
    })();
    return () => {
      mounted = false;
    };
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    await apiLogin(email, password);
    const me = await getMe();
    setUser(me);
    setCurrentUser(me.id);
    recordDailyLogin();
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    clearCurrentUser();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      login,
      logout,
      refreshUser,
    }),
    [user, loading, login, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
