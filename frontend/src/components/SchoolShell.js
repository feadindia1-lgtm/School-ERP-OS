import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  ChartLineUp, Buildings, Users, ShieldCheck, ClockCounterClockwise, SignOut,
  User as UserIcon, House, GraduationCap, ChalkboardTeacher, Coins, ClipboardText,
  Books, EnvelopeSimple, Sparkle, Kanban, Wall, Calendar, Gear, BookOpen,
  DoorOpen, Bell, UsersThree, IdentificationBadge, AirplaneTilt,
  Clock, QrCode, MapPin, PencilSimple, ListChecks,
} from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import ImpersonationBanner from "@/components/ImpersonationBanner";
import { api } from "@/lib/api";

const NAV_TOP = [
  { to: "/school", icon: House, label: "Overview", testid: "sch-nav-overview", end: true },
];

const NAV_ADMISSIONS = [
  { to: "/school/admissions", icon: ChartLineUp, label: "Dashboard", testid: "sch-nav-admissions-dashboard", end: true },
  { to: "/school/admissions/inquiries", icon: Kanban, label: "Inquiries", testid: "sch-nav-inquiries" },
  { to: "/school/admissions/applications", icon: ClipboardText, label: "Applications", testid: "sch-nav-applications" },
  { to: "/school/admissions/visits", icon: Calendar, label: "Campus Visits", testid: "sch-nav-visits" },
  { to: "/school/admissions/config", icon: Gear, label: "Configuration", testid: "sch-nav-config" },
];

export default function SchoolShell() {
  const { user, logout, tenant } = useAuth();
  const navigate = useNavigate();
  const [themeApplied, setThemeApplied] = useState(false);

  // Inherit tenant branding — primary color drives --klein var scope for the school area.
  useEffect(() => {
    if (!tenant?.branding) return;
    const b = tenant.branding;
    const root = document.getElementById("school-shell-root");
    if (root) {
      if (b.primary_color) root.style.setProperty("--klein", b.primary_color);
      if (b.accent_color) root.style.setProperty("--accent-yellow", b.accent_color);
    }
    setThemeApplied(true);
  }, [tenant?.branding]);

  return (
    <div id="school-shell-root" className="min-h-screen bg-[var(--paper)]" data-testid="school-shell">
      <ImpersonationBanner />
      <div className="flex">
        {/* Sidebar */}
        <aside data-testid="school-sidebar" className="hidden lg:flex w-[260px] shrink-0 border-r border-[var(--tinted-grey-200)] bg-white min-h-screen sticky top-0 flex-col">
          <div className="px-6 py-5 border-b border-[var(--tinted-grey-200)]">
            <div className="flex items-center gap-2">
              {tenant?.branding?.logo_url ? (
                <img src={tenant.branding.logo_url} alt="" className="h-7 w-7 object-contain" />
              ) : (
                <div className="h-7 w-7 bg-[var(--klein)] flex items-center justify-center rounded-[3px]">
                  <span className="font-heading text-white font-black text-sm leading-none">
                    {(tenant?.short_name || tenant?.name || "S").charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
              <div className="min-w-0">
                <div className="font-heading font-black tracking-tight leading-none truncate" data-testid="shell-school-name">
                  {tenant?.short_name || tenant?.name || "School OS"}
                </div>
                <div className="overline text-[10px] mt-1">School Console</div>
              </div>
            </div>
          </div>

          <nav className="flex-1 py-4 px-3 space-y-4 overflow-y-auto">
            <div className="space-y-1">
              {NAV_TOP.map((n) => <SidebarLink key={n.to} {...n} />)}
            </div>

            <div>
              <div className="overline px-3 mb-2 text-[9px]">Front Porch</div>
              <div className="space-y-1">
                {NAV_ADMISSIONS.map((n) => <SidebarLink key={n.to} {...n} />)}
              </div>
            </div>

            <div>
              <div className="overline px-3 mb-2 text-[9px]">Student Master</div>
              <div className="space-y-1">
                <SidebarLink to="/school/students" icon={GraduationCap} label="Students" testid="sch-nav-students" />
                <SidebarLink to="/school/guardians" icon={ChalkboardTeacher} label="Guardians" testid="sch-nav-guardians" />
                <SidebarLink to="/school/families" icon={Users} label="Families" testid="sch-nav-families" />
              </div>
            </div>

            <div>
              <div className="overline px-3 mb-2 text-[9px]">Academics</div>
              <div className="space-y-1">
                <SidebarLink to="/school/academic" icon={ChartLineUp} label="Overview" testid="sch-nav-academic-overview" end />
                <SidebarLink to="/school/academic/years" icon={Calendar} label="Academic years" testid="sch-nav-academic-years" />
                <SidebarLink to="/school/academic/classes-sections" icon={GraduationCap} label="Classes & sections" testid="sch-nav-classes-sections" />
                <SidebarLink to="/school/academic/subjects" icon={BookOpen} label="Subjects" testid="sch-nav-subjects" />
                <SidebarLink to="/school/academic/rooms" icon={DoorOpen} label="Rooms" testid="sch-nav-rooms" />
                <SidebarLink to="/school/academic/bell-schedule" icon={Bell} label="Bell schedule" testid="sch-nav-bell" />
                <SidebarLink to="/school/academic/calendar" icon={Calendar} label="School calendar" testid="sch-nav-calendar" />
                <SidebarLink to="/school/academic/assignments" icon={UsersThree} label="Teacher assignments" testid="sch-nav-assignments" />
                <SidebarLink to="/school/academic/board-config" icon={Gear} label="Board config" testid="sch-nav-board-config" />
              </div>
            </div>

            <div>
              <div className="overline px-3 mb-2 text-[9px]">Staff</div>
              <div className="space-y-1">
                <SidebarLink to="/school/staff" icon={IdentificationBadge} label="Employees" testid="sch-nav-staff" end />
                <SidebarLink to="/school/staff/dept-desig" icon={Buildings} label="Departments & designations" testid="sch-nav-dept-desig" />
                <SidebarLink to="/school/staff/leave-types" icon={Gear} label="Leave types" testid="sch-nav-leave-types" />
                <SidebarLink to="/school/staff/leaves" icon={AirplaneTilt} label="Leave applications" testid="sch-nav-leaves" />
              </div>
            </div>

            <div>
              <div className="overline px-3 mb-2 text-[9px]">Attendance</div>
              <div className="space-y-1">
                <SidebarLink to="/school/attendance/register" icon={ListChecks} label="Register" testid="sch-nav-att-register" />
                <SidebarLink to="/school/attendance/clock" icon={Clock} label="Staff clock-in" testid="sch-nav-att-clock" />
                <SidebarLink to="/school/attendance/scan" icon={QrCode} label="Gate scanner" testid="sch-nav-att-scan" />
                <SidebarLink to="/school/attendance/class" icon={ChalkboardTeacher} label="Class attendance" testid="sch-nav-att-class" />
                <SidebarLink to="/school/attendance/corrections" icon={PencilSimple} label="Corrections" testid="sch-nav-att-corr" />
                <SidebarLink to="/school/attendance/config" icon={MapPin} label="Config" testid="sch-nav-att-config" />
              </div>
            </div>

            <div>
              <div className="overline px-3 mb-2 text-[9px]">Administration</div>
              <div className="space-y-1">
                <SidebarLink to="/school/users" icon={Users} label="Users" testid="sch-nav-users" />
                <SidebarLink to="/school/rbac" icon={ShieldCheck} label="Roles" testid="sch-nav-rbac" />
                <SidebarLink to="/school/audit" icon={ClockCounterClockwise} label="Audit log" testid="sch-nav-audit" />
              </div>
            </div>
          </nav>

          <div className="border-t border-[var(--tinted-grey-200)] p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="h-8 w-8 bg-[var(--tinted-grey-100)] rounded-full flex items-center justify-center">
                <UserIcon size={16} weight="duotone" />
              </div>
              <div className="min-w-0">
                <div className="text-xs font-mono truncate" data-testid="header-user-email">{user?.email}</div>
                <div className="overline text-[9px]" data-testid="header-user-role">{user?.role?.replace(/_/g, " ")}</div>
              </div>
            </div>
            <button
              data-testid="header-logout-btn"
              onClick={async () => { await logout(); navigate("/"); }}
              className="w-full flex items-center gap-2 text-xs text-[var(--tinted-grey-500)] hover:text-[var(--accent-red)] transition-colors"
            >
              <SignOut size={14} /> Sign out
            </button>
          </div>
        </aside>

        {/* Mobile bar */}
        <div className="lg:hidden fixed top-0 inset-x-0 bg-white border-b border-[var(--tinted-grey-200)] z-30 h-14 flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 bg-[var(--klein)] flex items-center justify-center rounded-[3px]">
              <span className="font-heading text-white font-black text-xs leading-none">
                {(tenant?.short_name || tenant?.name || "S").charAt(0).toUpperCase()}
              </span>
            </div>
            <span className="font-heading font-black">{tenant?.short_name || tenant?.name || "School"}</span>
          </div>
          <button data-testid="mobile-signout" onClick={async () => { await logout(); navigate("/"); }}><SignOut size={20} /></button>
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

function SidebarLink({ to, icon: Icon, label, testid, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      data-testid={testid}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 text-sm rounded-none transition-colors ${
          isActive
            ? "bg-[var(--ink)] text-white"
            : "text-[var(--tinted-grey-500)] hover:bg-[var(--tinted-grey-100)] hover:text-[var(--ink)]"
        }`
      }
    >
      <Icon size={16} weight="duotone" />
      <span>{label}</span>
    </NavLink>
  );
}
