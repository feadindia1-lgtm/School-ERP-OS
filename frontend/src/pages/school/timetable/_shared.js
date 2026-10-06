/**
 * Timetable module — shared hooks + constants.
 *
 * Reuses the academic year hook from the academics module.  Loads the
 * tenant's working-day policy and the default bell schedule so the grid
 * knows which columns (weekdays) and rows (periods) to render.
 */
import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

export const WEEKDAY_LABELS = {
  mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun",
};

const STORAGE_YEAR = "schoolos.academic_year_id";
const STORAGE_SECTION = "schoolos.timetable.section_id";
const STORAGE_DATE = "schoolos.proxy.date";

export function useYearPicker() {
  const [years, setYears] = useState([]);
  const [yearId, setYearId] = useState(() => localStorage.getItem(STORAGE_YEAR) || "");
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    try {
      setLoading(true);
      const { data } = await api.get("/school/academic/years");
      setYears(data);
      if (!localStorage.getItem(STORAGE_YEAR)) {
        const current = data.find((y) => y.is_current) || data[0];
        if (current) { setYearId(current.id); localStorage.setItem(STORAGE_YEAR, current.id); }
      }
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const choose = useCallback((id) => { setYearId(id); localStorage.setItem(STORAGE_YEAR, id); }, []);
  return { years, yearId, setYearId: choose, loading };
}

export function useSectionPicker(yearId) {
  const [classes, setClasses] = useState([]);
  const [sections, setSections] = useState([]);
  const [classId, setClassId] = useState("");
  const [sectionId, setSectionIdState] = useState(() => localStorage.getItem(STORAGE_SECTION) || "");
  const loadClasses = useCallback(async () => {
    if (!yearId) return;
    try {
      const { data } = await api.get("/school/academic/classes", { params: { academic_year_id: yearId } });
      setClasses(data);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [yearId]);
  const loadSections = useCallback(async () => {
    if (!yearId) return;
    try {
      const { data } = await api.get("/school/academic/sections", { params: { academic_year_id: yearId } });
      setSections(data);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [yearId]);
  useEffect(() => { loadClasses(); loadSections(); }, [loadClasses, loadSections]);
  useEffect(() => {
    const sec = sections.find((s) => s.id === sectionId);
    if (sec) setClassId(sec.class_id);
  }, [sections, sectionId]);
  const setSectionId = useCallback((id) => { setSectionIdState(id); localStorage.setItem(STORAGE_SECTION, id); }, []);
  const sectionsForClass = classId ? sections.filter((s) => s.class_id === classId) : sections;
  return { classes, sections, sectionsForClass, classId, setClassId, sectionId, setSectionId };
}

export function useDatePicker(defaultValue) {
  const [date, setDateState] = useState(() => localStorage.getItem(STORAGE_DATE) || defaultValue || new Date().toISOString().slice(0, 10));
  const setDate = useCallback((d) => { setDateState(d); localStorage.setItem(STORAGE_DATE, d); }, []);
  return { date, setDate };
}

export async function fetchBellSchedules(yearId) {
  const { data } = await api.get("/school/academic/bell-schedules", { params: { academic_year_id: yearId } });
  return data;
}

export async function fetchGrid(yearId, sectionId) {
  const { data } = await api.get("/school/timetable/grid", { params: { academic_year_id: yearId, section_id: sectionId } });
  return data;
}

export async function fetchTeachers() {
  const { data } = await api.get("/school/users");
  return (data || []).filter((u) => u.role === "teacher" || u.role === "class_teacher");
}

export async function fetchSubjects() {
  const { data } = await api.get("/school/academic/subjects");
  return data;
}

export async function fetchRooms() {
  const { data } = await api.get("/school/academic/rooms");
  return data;
}

export const SUB_STATUS_TONE = {
  recommended: "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]",
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-[var(--klein)] text-white",
  rejected: "bg-[var(--accent-red)]/10 text-[var(--accent-red)]",
  cancelled: "bg-[var(--tinted-grey-200)] text-[var(--tinted-grey-500)]",
};
