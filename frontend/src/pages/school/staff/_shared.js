/**
 * Shared helpers for the Staff / Leave module.
 */
import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

export const EMPLOYMENT_TYPES = ["full_time", "part_time", "contract", "visiting", "intern", "consultant"];
export const EMPLOYMENT_STATUSES = [
  "active", "probation", "on_leave", "suspended", "resigned",
  "terminated", "retired", "notice_period",
];
export const LEAVE_APPLICABLE_TO = ["all", "teaching", "non_teaching", "male", "female", "specific"];
export const LEAVE_ACCRUAL_FREQ = ["yearly", "monthly", "quarterly", "one_time"];
export const LEAVE_STATUS_TONE = {
  pending: "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]",
  approved_l1: "bg-[var(--accent-yellow)] text-[var(--ink)]",
  approved: "bg-[var(--klein)] text-white",
  rejected: "bg-[var(--accent-red)] text-white",
  cancelled: "bg-[var(--tinted-grey-300)] text-[var(--ink)]",
  withdrawn: "bg-[var(--tinted-grey-300)] text-[var(--ink)]",
};
export const STATUS_TONE = {
  active: "bg-[var(--klein)] text-white",
  probation: "bg-[var(--accent-yellow)] text-[var(--ink)]",
  on_leave: "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]",
  resigned: "bg-[var(--tinted-grey-500)] text-white",
  terminated: "bg-[var(--accent-red)] text-white",
  retired: "bg-[var(--tinted-grey-500)] text-white",
  suspended: "bg-[var(--accent-red)] text-white",
  notice_period: "bg-[var(--accent-yellow)] text-[var(--ink)]",
};

export function useStaffMeta() {
  const [meta, setMeta] = useState({ departments: [], designations: [], leaveTypes: [] });
  const load = useCallback(async () => {
    try {
      const [d, g, lt] = await Promise.all([
        api.get("/school/staff/departments"),
        api.get("/school/staff/designations"),
        api.get("/school/staff/leave-types"),
      ]);
      setMeta({ departments: d.data, designations: g.data, leaveTypes: lt.data.items || [] });
    } catch (e) { toast.error(formatApiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);
  return { ...meta, reload: load };
}
