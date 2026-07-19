import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { getAccessToken } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { loading } = useAuth();
  const location = useLocation();

  // No token at all — bounce to login immediately.
  if (!getAccessToken()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // Token present but still validating /users/me.
  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner" aria-label="Loading" />
      </div>
    );
  }

  return <>{children}</>;
}
