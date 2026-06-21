import { Link, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { isManagerRole } from "../lib/auth";

export function AppLayout() {
  const { user, organization, role, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div>
            <Link to="/" className="text-lg font-semibold text-slate-900">
              ShiftOps
            </Link>
            {organization && (
              <p className="text-sm text-slate-500">{organization.name}</p>
            )}
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-slate-600">
              {user?.full_name} · {role}
            </span>
            {isManagerRole(role ?? "") && (
              <>
                <Link to="/manager/schedule" className="text-blue-600 hover:underline">
                  Schedule
                </Link>
                <Link to="/manager/coverage/new" className="text-blue-600 hover:underline">
                  New coverage
                </Link>
              </>
            )}
            {role === "EMPLOYEE" && (
              <Link to="/employee/shifts" className="text-blue-600 hover:underline">
                My shifts
              </Link>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-md border border-slate-300 px-3 py-1.5 hover:bg-slate-50"
            >
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
