import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { CreateCoveragePage } from "./pages/CreateCoveragePage";
import { EmployeeAvailabilityPage } from "./pages/EmployeeAvailabilityPage";
import { EmployeeDocumentsPage } from "./pages/EmployeeDocumentsPage";
import { EmployeeShiftsPage } from "./pages/EmployeeShiftsPage";
import { EmployeeTimeOffPage } from "./pages/EmployeeTimeOffPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { ManagerEmployeeAvailabilityPage } from "./pages/ManagerEmployeeAvailabilityPage";
import { ManagerActivityLogPage } from "./pages/ManagerActivityLogPage";
import { ManagerEmployeeDocumentsPage } from "./pages/ManagerEmployeeDocumentsPage";
import { ManagerSchedulePage } from "./pages/ManagerSchedulePage";
import { ManagerShiftSwapsPage } from "./pages/ManagerShiftSwapsPage";
import { ManagerTimeOffPage } from "./pages/ManagerTimeOffPage";
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
              <Route path="/manager/time-off" element={<ManagerTimeOffPage />} />
              <Route path="/manager/shift-swaps" element={<ManagerShiftSwapsPage />} />
              <Route path="/manager/activity" element={<ManagerActivityLogPage />} />
              <Route
                path="/manager/employee-documents"
                element={<ManagerEmployeeDocumentsPage />}
              />
              <Route
                path="/manager/employee-availability"
                element={<ManagerEmployeeAvailabilityPage />}
              />
            </Route>
          </Route>

          <Route element={<ProtectedRoute employeeOnly />}>
            <Route element={<AppLayout />}>
              <Route path="/employee/shifts" element={<EmployeeShiftsPage />} />
              <Route path="/employee/availability" element={<EmployeeAvailabilityPage />} />
              <Route path="/employee/time-off" element={<EmployeeTimeOffPage />} />
              <Route path="/employee/documents" element={<EmployeeDocumentsPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
