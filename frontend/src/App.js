import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/context/ProtectedRoute";
import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/pages/LoginPage";
import RegisterSchoolPage from "@/pages/RegisterSchoolPage";
import SchoolConsolePage from "@/pages/SchoolConsolePage";
import PlatformShell from "@/components/PlatformShell";
import PlatformDashboardPage from "@/pages/platform/PlatformDashboardPage";
import PlatformSchoolsPage from "@/pages/platform/PlatformSchoolsPage";
import PlatformSchoolNewPage from "@/pages/platform/PlatformSchoolNewPage";
import PlatformSchoolDetailPage from "@/pages/platform/PlatformSchoolDetailPage";
import PlatformAlertsPage from "@/pages/platform/PlatformAlertsPage";
import PlatformAuditPage from "@/pages/platform/PlatformAuditPage";

export default function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Toaster position="top-right" richColors closeButton />
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterSchoolPage />} />

            {/* Platform Console — sidebar shell with nested pages */}
            <Route
              path="/platform"
              element={
                <ProtectedRoute requirePlatform>
                  <PlatformShell />
                </ProtectedRoute>
              }
            >
              <Route index element={<PlatformDashboardPage />} />
              <Route path="schools" element={<PlatformSchoolsPage />} />
              <Route path="schools/new" element={<PlatformSchoolNewPage />} />
              <Route path="schools/:id" element={<PlatformSchoolDetailPage />} />
              <Route path="alerts" element={<PlatformAlertsPage />} />
              <Route path="audit" element={<PlatformAuditPage />} />
            </Route>

            {/* School Console — impersonated platform admins land here too */}
            <Route
              path="/school"
              element={
                <ProtectedRoute requireSchool>
                  <SchoolConsolePage />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}
