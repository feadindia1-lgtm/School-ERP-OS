import { WarningOctagon, SignOut } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

export default function ImpersonationBanner() {
  const { impersonation, exitImpersonation } = useAuth();
  const navigate = useNavigate();
  if (!impersonation) return null;

  const exit = async () => {
    const res = await exitImpersonation();
    if (!res.ok) return toast.error(res.error);
    toast.success("Exited support mode");
    navigate("/platform");
  };

  return (
    <div data-testid="impersonation-banner" className="sticky top-0 z-50 bg-[var(--accent-yellow)] text-[var(--ink)] border-b-2 border-[var(--ink)]">
      <div className="max-w-[1400px] mx-auto flex flex-wrap items-center justify-between gap-3 px-6 lg:px-10 h-11 text-sm">
        <div className="flex items-center gap-2">
          <WarningOctagon size={18} weight="fill" />
          <span className="font-heading font-bold">SUPPORT MODE</span>
          <span className="hidden md:inline">·</span>
          <span className="hidden md:inline">Impersonating — reason: <span className="font-mono">{impersonation.reason}</span></span>
          <span className="md:hidden font-mono text-xs">{impersonation.reason}</span>
        </div>
        <button
          data-testid="impersonation-exit"
          onClick={exit}
          className="inline-flex items-center gap-1 bg-[var(--ink)] text-white px-3 py-1 hover:bg-[var(--klein)] transition-colors font-semibold"
        >
          <SignOut size={14} /> Exit support mode
        </button>
      </div>
    </div>
  );
}
