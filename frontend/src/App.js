import "@/App.css";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/context/ProtectedRoute";
import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/pages/LoginPage";
import RegisterSchoolPage from "@/pages/RegisterSchoolPage";
import PlatformConsolePage from "@/pages/PlatformConsolePage";
import SchoolConsolePage from "@/pages/SchoolConsolePage";

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
              element={
                <ProtectedRoute requirePlatform>
                  <PlatformConsolePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/school"
              element={
                <ProtectedRoute requireSchool>
                  <SchoolConsolePage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}
