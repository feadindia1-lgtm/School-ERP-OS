import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  UsersThree, PhoneCall, Calendar, ClipboardText, CheckCircle, XCircle,
  ChartPieSlice, GraduationCap, TrendUp,
} from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

function Kpi({ icon: Icon, label, value, hint, tone = "default", to, testid }) {
  const border =
    tone === "critical" ? "border-[var(--accent-red)]" :
    tone === "warning" ? "border-[var(--accent-yellow)]" :
    "border-[var(--tinted-grey-200)]";
  const inner = (
    <>
      <div className="flex items-start justify-between">
        <Icon size={20} weight="duotone" className="text-[var(--klein)]" />
        <span className="overline">{label}</span>
      </div>
      <div className="mt-6 font-heading font-black text-4xl tracking-tight tabular">{value}</div>
      {hint && <div className="mt-1 text-xs text-[var(--tinted-grey-500)]">{hint}</div>}
    </>
  );
  const cls = `bg-white border ${border} p-6 h-full block`;
  return to ? (
    <Link to={to} data-testid={testid} className={cls}>{inner}</Link>
  ) : (
    <motion.div whileHover={{ y: -3 }} transition={{ duration: 0.2 }} data-testid={testid} className={cls}>
      {inner}
    </motion.div>
  );
}

export default function AdmissionsDashboardPage() {
  const [d, setD] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/school/crm/dashboard");
        setD(data);
      } catch (e) { toast.error(formatApiError(e)); }
    })();
  }, []);

  return (
    <div data-testid="admissions-dashboard">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Front Porch</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="admissions-title">
            Admissions
          </h1>
        </div>
        <Link to="/school/admissions/inquiries">
          <Button data-testid="admissions-cta-inquiries" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white transition-opacity">
            Open pipeline
          </Button>
        </Link>
      </div>

      <div className="mt-10 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 lg:gap-6">
        <Kpi icon={UsersThree} label="Total inquiries" value={d?.total_inquiries ?? "—"} hint={`${d?.new_inquiries_7d ?? 0} new · 7d`} testid="kpi-total-inquiries" />
        <Kpi icon={PhoneCall} label="Follow-ups today" value={d?.followups_due_today ?? "—"} tone="warning" testid="kpi-followups-today" />
        <Kpi icon={PhoneCall} label="Overdue" value={d?.overdue_followups ?? "—"} tone={d?.overdue_followups ? "critical" : "default"} testid="kpi-overdue" />
        <Kpi icon={Calendar} label="Visits (7d)" value={d?.upcoming_visits_7d ?? "—"} testid="kpi-visits" />
        <Kpi icon={ClipboardText} label="In progress" value={d?.applications_in_progress ?? "—"} hint="Applications" testid="kpi-in-progress" />
        <Kpi icon={ChartPieSlice} label="Pending review" value={d?.applications_pending_review ?? "—"} testid="kpi-pending-review" />
        <Kpi icon={CheckCircle} label="Approved" value={d?.applications_approved ?? "—"} testid="kpi-approved" />
        <Kpi icon={GraduationCap} label="Admitted" value={d?.admissions_confirmed ?? "—"} testid="kpi-admitted" />
        <Kpi icon={XCircle} label="Lost / Rejected" value={d?.lost_or_rejected ?? "—"} tone={(d?.lost_or_rejected ?? 0) > 0 ? "critical" : "default"} testid="kpi-lost" />
        <Kpi icon={TrendUp} label="Conversion" value={`${d?.conversion_rate ?? 0}%`} testid="kpi-conversion" />
      </div>

      <div className="mt-12 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BreakdownCard title="By stage" testid="breakdown-stage" data={d?.stage_counts} />
        <BreakdownCard title="By source" testid="breakdown-source" data={d?.source_counts} />
      </div>
    </div>
  );
}

function BreakdownCard({ title, data, testid }) {
  const entries = Object.entries(data || {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map(([, n]) => n));
  return (
    <div className="bg-white border border-[var(--tinted-grey-200)] p-6" data-testid={testid}>
      <div className="overline">{title}</div>
      <div className="mt-4 space-y-3">
        {entries.length === 0 && <div className="text-sm text-[var(--tinted-grey-500)]">No data yet.</div>}
        {entries.map(([k, n]) => (
          <div key={k}>
            <div className="flex justify-between text-xs mb-1">
              <span className="uppercase tracking-widest">{k}</span>
              <span className="font-mono tabular">{n}</span>
            </div>
            <div className="h-1.5 bg-[var(--tinted-grey-100)]">
              <div className="h-full bg-[var(--klein)]" style={{ width: `${(n / max) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
