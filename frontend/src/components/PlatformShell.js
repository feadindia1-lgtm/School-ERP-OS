import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  ChartLineUp, Buildings, Bell, ClockCounterClockwise, SignOut, User as UserIcon, House,
} from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import ImpersonationBanner from "@/components/ImpersonationBanner";

const NAV = [
  { to: "/platform", icon: ChartLineUp, label: "Dashboard", testid: "nav-dashboard", end: true },
  { to: "/platform/schools", icon: Buildings, label: "Schools", testid: "nav-schools" },
  { to: "/platform/alerts", icon: Bell, label: "Alerts", testid: "nav-alerts" },
  { to: "/platform/audit", icon: ClockCounterClockwise, label: "Audit log", testid: "nav-audit" },
];

export default function PlatformShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[var(--paper)]" data-testid="platform-shell">
      <ImpersonationBanner />
      <div className="flex">
        {/* Sidebar */}
        <aside data-testid="platform-sidebar" className="hidden lg:flex w-[260px] shrink-0 border-r border-[var(--tinted-grey-200)] bg-white min-h-screen sticky top-0 flex-col">
          <div className="px-6 py-5 border-b border-[var(--tinted-grey-200)]">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 bg-[var(--klein)] flex items-center justify-center rounded-[3px]">
                <span className="font-heading text-white font-black text-sm leading-none">S</span>
              </div>
              <div>
                <div className="font-heading font-black tracking-tight leading-none">School OS</div>
                <div className="overline text-[10px] mt-1">Platform Console</div>
              </div>
            </div>
          </div>

          <nav className="flex-1 py-6 px-3 space-y-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                data-testid={n.testid}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 text-sm rounded-none transition-colors ${
                    isActive
                      ? "bg-[var(--ink)] text-white"
                      : "text-[var(--tinted-grey-500)] hover:bg-[var(--tinted-grey-100)] hover:text-[var(--ink)]"
                  }`
                }
              >
                <n.icon size={18} weight="duotone" />
                <span>{n.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-[var(--tinted-grey-200)] p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="h-8 w-8 bg-[var(--tinted-grey-100)] rounded-full flex items-center justify-center">
                <UserIcon size={16} weight="duotone" />
              </div>
              <div className="min-w-0">
                <div className="text-xs font-mono truncate" data-testid="sidebar-user-email">{user?.email}</div>
                <div className="overline text-[9px]">Platform superadmin</div>
              </div>
            </div>
            <button
              data-testid="sidebar-logout"
              onClick={async () => { await logout(); navigate("/"); }}
              className="w-full flex items-center gap-2 text-xs text-[var(--tinted-grey-500)] hover:text-[var(--accent-red)] transition-colors"
            >
              <SignOut size={14} /> Sign out
            </button>
          </div>
        </aside>

        {/* Mobile top bar */}
        <div className="lg:hidden fixed top-0 inset-x-0 bg-white border-b border-[var(--tinted-grey-200)] z-30 h-14 flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 bg-[var(--klein)] flex items-center justify-center rounded-[3px]">
              <span className="font-heading text-white font-black text-xs leading-none">S</span>
            </div>
            <span className="font-heading font-black">School OS</span>
          </div>
          <button data-testid="mobile-home" onClick={() => navigate("/platform")}><House size={20} /></button>
        </div>

        <main className="flex-1 min-w-0 lg:pt-0 pt-14">
          <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-8 lg:py-10">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
