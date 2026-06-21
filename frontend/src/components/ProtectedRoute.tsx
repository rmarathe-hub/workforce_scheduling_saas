import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { isManagerRole } from "../shared/auth";

interface ProtectedRouteProps {
  managerOnly?: boolean;
  employeeOnly?: boolean;
}

export function ProtectedRoute({ managerOnly, employeeOnly }: ProtectedRouteProps) {
  const { token, role, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-600">
        Loading...
      </div>
    );
  }

  if (!token || !role) {
    return <Navigate to="/login" replace />;
  }

  if (managerOnly && !isManagerRole(role)) {
    return <Navigate to="/employee/shifts" replace />;
  }

  if (employeeOnly && isManagerRole(role)) {
    return <Navigate to="/manager/schedule" replace />;
  }

  return <Outlet />;
}
