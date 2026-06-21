import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { isManagerRole } from "../lib/auth";

export function HomePage() {
  const { token, role, isLoading } = useAuth();

  if (isLoading) {
    return <div className="text-slate-600">Loading...</div>;
  }

  if (!token || !role) {
    return <Navigate to="/login" replace />;
  }

  if (isManagerRole(role)) {
    return <Navigate to="/manager/schedule" replace />;
  }

  return <Navigate to="/employee/shifts" replace />;
}
