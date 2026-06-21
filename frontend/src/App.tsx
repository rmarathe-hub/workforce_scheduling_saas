import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { CreateCoveragePage } from "./pages/CreateCoveragePage";
import { EmployeeShiftsPage } from "./pages/EmployeeShiftsPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { ManagerSchedulePage } from "./pages/ManagerSchedulePage";
import { RegisterPage } from "./pages/RegisterPage";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<HomePage />} />
            </Route>
          </Route>

          <Route element={<ProtectedRoute managerOnly />}>
            <Route element={<AppLayout />}>
              <Route path="/manager/schedule" element={<ManagerSchedulePage />} />
              <Route path="/manager/coverage/new" element={<CreateCoveragePage />} />
            </Route>
          </Route>

          <Route element={<ProtectedRoute employeeOnly />}>
            <Route element={<AppLayout />}>
              <Route path="/employee/shifts" element={<EmployeeShiftsPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
