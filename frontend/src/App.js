import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/context/ProtectedRoute";
import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/pages/LoginPage";
import RegisterSchoolPage from "@/pages/RegisterSchoolPage";
import SchoolConsolePage from "@/pages/SchoolConsolePage";
import SchoolShell from "@/components/SchoolShell";
import AdmissionsDashboardPage from "@/pages/school/AdmissionsDashboardPage";
import InquiriesPage from "@/pages/school/InquiriesPage";
import InquiryDetailPage from "@/pages/school/InquiryDetailPage";
import ApplicationsPage from "@/pages/school/ApplicationsPage";
import ApplicationDetailPage from "@/pages/school/ApplicationDetailPage";
import CampusVisitsPage from "@/pages/school/CampusVisitsPage";
import CrmConfigPage from "@/pages/school/CrmConfigPage";
import StudentsPage from "@/pages/school/StudentsPage";
import StudentDetailPage from "@/pages/school/StudentDetailPage";
import GuardiansPage from "@/pages/school/GuardiansPage";
import GuardianDetailPage from "@/pages/school/GuardianDetailPage";
import FamiliesPage from "@/pages/school/FamiliesPage";
import FamilyDetailPage from "@/pages/school/FamilyDetailPage";
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

            <Route
              path="/platform"
              element={<ProtectedRoute requirePlatform><PlatformShell /></ProtectedRoute>}
            >
              <Route index element={<PlatformDashboardPage />} />
              <Route path="schools" element={<PlatformSchoolsPage />} />
              <Route path="schools/new" element={<PlatformSchoolNewPage />} />
              <Route path="schools/:id" element={<PlatformSchoolDetailPage />} />
              <Route path="alerts" element={<PlatformAlertsPage />} />
              <Route path="audit" element={<PlatformAuditPage />} />
            </Route>

            <Route
              path="/school"
              element={<ProtectedRoute requireSchool><SchoolShell /></ProtectedRoute>}
            >
              <Route index element={<SchoolConsolePage />} />
              <Route path="users" element={<SchoolConsolePage />} />
              <Route path="rbac" element={<SchoolConsolePage />} />
              <Route path="audit" element={<SchoolConsolePage />} />
              <Route path="admissions" element={<AdmissionsDashboardPage />} />
              <Route path="admissions/inquiries" element={<InquiriesPage />} />
              <Route path="admissions/inquiries/:id" element={<InquiryDetailPage />} />
              <Route path="admissions/applications" element={<ApplicationsPage />} />
              <Route path="admissions/applications/:id" element={<ApplicationDetailPage />} />
              <Route path="admissions/visits" element={<CampusVisitsPage />} />
              <Route path="admissions/config" element={<CrmConfigPage />} />
              <Route path="students" element={<StudentsPage />} />
              <Route path="students/:id" element={<StudentDetailPage />} />
              <Route path="guardians" element={<GuardiansPage />} />
              <Route path="guardians/:id" element={<GuardianDetailPage />} />
              <Route path="families" element={<FamiliesPage />} />
              <Route path="families/:id" element={<FamilyDetailPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}
