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
import AcademicOverviewPage from "@/pages/school/academic/AcademicOverviewPage";
import AcademicYearsPage from "@/pages/school/academic/AcademicYearsPage";
import ClassesSectionsPage from "@/pages/school/academic/ClassesSectionsPage";
import SubjectsPage from "@/pages/school/academic/SubjectsPage";
import RoomsPage from "@/pages/school/academic/RoomsPage";
import BellScheduleEditorPage from "@/pages/school/academic/BellScheduleEditorPage";
import WorkingDaysHolidaysPage from "@/pages/school/academic/WorkingDaysHolidaysPage";
import TeacherAssignmentsPage from "@/pages/school/academic/TeacherAssignmentsPage";
import BoardConfigPage from "@/pages/school/academic/BoardConfigPage";
import StaffPage from "@/pages/school/staff/StaffPage";
import StaffDetailPage from "@/pages/school/staff/StaffDetailPage";
import DepartmentsDesignationsPage from "@/pages/school/staff/DepartmentsDesignationsPage";
import LeaveTypesPage from "@/pages/school/staff/LeaveTypesPage";
import LeaveApplicationsPage from "@/pages/school/staff/LeaveApplicationsPage";
import StaffClockPage from "@/pages/school/attendance/StaffClockPage";
import StudentScannerPage from "@/pages/school/attendance/StudentScannerPage";
import ClassAttendanceMarkerPage from "@/pages/school/attendance/ClassAttendanceMarkerPage";
import { AttendanceRegisterPage, CorrectionsPage, AttendanceConfigPage } from "@/pages/school/attendance/pages";
import TimetableGridPage from "@/pages/school/timetable/TimetableGridPage";
import ProxyDashboardPage from "@/pages/school/timetable/ProxyDashboardPage";
import ProxyConfigPage from "@/pages/school/timetable/ProxyConfigPage";
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
              <Route path="academic" element={<AcademicOverviewPage />} />
              <Route path="academic/years" element={<AcademicYearsPage />} />
              <Route path="academic/classes-sections" element={<ClassesSectionsPage />} />
              <Route path="academic/subjects" element={<SubjectsPage />} />
              <Route path="academic/rooms" element={<RoomsPage />} />
              <Route path="academic/bell-schedule" element={<BellScheduleEditorPage />} />
              <Route path="academic/calendar" element={<WorkingDaysHolidaysPage />} />
              <Route path="academic/assignments" element={<TeacherAssignmentsPage />} />
              <Route path="academic/board-config" element={<BoardConfigPage />} />
              <Route path="staff" element={<StaffPage />} />
              <Route path="staff/dept-desig" element={<DepartmentsDesignationsPage />} />
              <Route path="staff/leave-types" element={<LeaveTypesPage />} />
              <Route path="staff/leaves" element={<LeaveApplicationsPage />} />
              <Route path="staff/:id" element={<StaffDetailPage />} />
              <Route path="attendance/clock" element={<StaffClockPage />} />
              <Route path="attendance/scan" element={<StudentScannerPage />} />
              <Route path="attendance/class" element={<ClassAttendanceMarkerPage />} />
              <Route path="attendance/register" element={<AttendanceRegisterPage />} />
              <Route path="attendance/corrections" element={<CorrectionsPage />} />
              <Route path="attendance/config" element={<AttendanceConfigPage />} />
              <Route path="timetable" element={<TimetableGridPage />} />
              <Route path="timetable/proxy" element={<ProxyDashboardPage />} />
              <Route path="timetable/proxy-config" element={<ProxyConfigPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}
