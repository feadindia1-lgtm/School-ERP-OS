import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { GraduationCap, UsersThree, BookOpen, DoorOpen, Bell, Calendar, ChalkboardTeacher, Users } from "@phosphor-icons/react";
import { useAcademicYears, useCurrentYear, ACADEMIC_STATUS_TONE } from "./_shared";

const TILES = [
  { key: "classes", label: "Classes", icon: GraduationCap, href: "/school/academic/classes-sections", testid: "tile-classes" },
  { key: "sections", label: "Sections", icon: UsersThree, href: "/school/academic/classes-sections", testid: "tile-sections" },
  { key: "subjects", label: "Subjects", icon: BookOpen, href: "/school/academic/subjects", testid: "tile-subjects" },
  { key: "rooms", label: "Rooms", icon: DoorOpen, href: "/school/academic/rooms", testid: "tile-rooms" },
  { key: "bell_schedules", label: "Bell schedules", icon: Bell, href: "/school/academic/bell-schedule", testid: "tile-bell" },
  { key: "holidays", label: "Holidays", icon: Calendar, href: "/school/academic/calendar", testid: "tile-holidays" },
  { key: "teacher_assignments", label: "Assignments", icon: ChalkboardTeacher, href: "/school/academic/assignments", testid: "tile-assignments" },
  { key: "students_snapshot", label: "Students (year)", icon: Users, href: "/school/students", testid: "tile-students" },
];

export default function AcademicOverviewPage() {
  const { years } = useAcademicYears();
  const { yearId, setYearId, currentYear } = useCurrentYear(years);
  const [counts, setCounts] = useState({});

  const load = useCallback(async () => {
    if (!yearId) return;
    try {
      const { data } = await api.get(`/school/academic/overview/${yearId}`);
      setCounts(data.counts || {});
    } catch (e) { toast.error(formatApiError(e)); }
  }, [yearId]);
  useEffect(() => { load(); }, [load]);

  return (
    <div data-testid="academic-overview-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Academic Framework</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="ov-title">Academic overview</h1>
          {currentYear && (
            <div className="mt-2 text-sm text-[var(--tinted-grey-500)] flex items-center gap-2">
              <span>{currentYear.name}</span>
              <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${ACADEMIC_STATUS_TONE[currentYear.status] || ""}`} data-testid="ov-year-status">{currentYear.status}</span>
            </div>
          )}
        </div>
        <div className="flex gap-3">
          <Select value={yearId} onValueChange={setYearId}>
            <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="ov-year-select"><SelectValue placeholder="Select year" /></SelectTrigger>
            <SelectContent>{years.map(y => <SelectItem key={y.id} value={y.id} data-testid={`ovy-${y.id}`}>{y.name}{y.is_current ? " (current)" : ""}</SelectItem>)}</SelectContent>
          </Select>
          <Link to="/school/academic/years" className="klein-underline text-[var(--klein)] text-sm self-center" data-testid="ov-manage-years">Manage years →</Link>
        </div>
      </div>

      {!yearId ? (
        <div className="mt-8 bg-white border border-[var(--tinted-grey-200)] p-8 text-sm text-[var(--tinted-grey-500)]" data-testid="ov-empty">
          Create your first academic year to bootstrap the framework.
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="ov-tiles">
          {TILES.map(t => {
            const Icon = t.icon;
            return (
              <Link key={t.key} to={t.href} className="bg-white border border-[var(--tinted-grey-200)] p-5 hover:border-[var(--klein)] transition-colors" data-testid={t.testid}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="overline text-[10px]">{t.label}</div>
                    <div className="mt-2 font-heading font-black text-4xl tracking-tighter tabular-nums" data-testid={`${t.testid}-value`}>{counts[t.key] ?? 0}</div>
                  </div>
                  <div className="h-9 w-9 flex items-center justify-center bg-[var(--klein)] text-white"><Icon size={18} weight="duotone" /></div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
