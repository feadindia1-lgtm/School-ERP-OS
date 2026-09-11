/**
 * Shared helpers for the Academics module.
 *
 * The academic year is universally required across every academics page.
 * `useCurrentYear()` centralises the "load years, remember chosen id in
 * localStorage" flow so every page consistently shows the same year selector.
 */
import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

const STORAGE_KEY = "schoolos.academic_year_id";

export function useAcademicYears() {
  const [years, setYears] = useState([]);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    try {
      setLoading(true);
      const { data } = await api.get("/school/academic/years");
      setYears(data);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  return { years, loading, reload: load };
}

export function useCurrentYear(years) {
  const [yearId, setYearIdState] = useState(() => localStorage.getItem(STORAGE_KEY) || "");
  useEffect(() => {
    if (yearId && years.some((y) => y.id === yearId)) return;
    const current = years.find((y) => y.is_current) || years[0];
    if (current) { setYearIdState(current.id); localStorage.setItem(STORAGE_KEY, current.id); }
  }, [years, yearId]);
  const setYearId = useCallback((id) => {
    setYearIdState(id); localStorage.setItem(STORAGE_KEY, id);
  }, []);
  const currentYear = years.find((y) => y.id === yearId) || null;
  return { yearId, setYearId, currentYear };
}

export const ACADEMIC_STATUS_TONE = {
  planning: "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]",
  current: "bg-[var(--klein)] text-white",
  archived: "bg-[var(--tinted-grey-500)] text-white",
};

export const SUBJECT_TYPES = ["theory", "practical", "lab", "co_scholastic", "language", "elective"];
export const ROOM_TYPES = ["classroom", "lab", "auditorium", "library", "sports", "computer_lab", "other"];
export const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
export const WEEKDAY_LABELS = { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun" };
export const BOARD_PRESETS_LIST = ["CBSE", "ICSE", "IB", "IGCSE", "STATE", "CUSTOM"];
