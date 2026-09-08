import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--paper)]">
      <div className="flex flex-col items-start gap-3">
        <div className="overline">Loading</div>
        <div className="h-1 w-40 bg-[var(--tinted-grey-200)] overflow-hidden">
          <div className="h-full bg-[var(--klein)] animate-[loading_1.2s_ease_infinite]" style={{ width: "40%" }} />
        </div>
      </div>
      <style>{`@keyframes loading { 0% { transform: translateX(-100%);} 100% { transform: translateX(300%);} }`}</style>
    </div>
  );
}

export function ProtectedRoute({ children, requirePlatform, requireSchool }) {
  const { user } = useAuth();
  const location = useLocation();
  if (user === null) return <LoadingScreen />;
  if (user === false) return <Navigate to="/login" replace state={{ from: location }} />;

  const isPlatform = user.role === "platform_superadmin";
  if (requirePlatform && !isPlatform) return <Navigate to="/school" replace />;
  if (requireSchool && isPlatform) return <Navigate to="/platform" replace />;
  return children;
}
