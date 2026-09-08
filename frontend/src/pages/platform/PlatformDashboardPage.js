import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Buildings, CheckCircle, Hourglass, Prohibit, Users, GraduationCap, ChalkboardTeacher,
  Coins, Bell, ArrowRight, Warning,
} from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

function Kpi({ icon: Icon, label, value, hint, tone = "default", testid }) {
  const border =
    tone === "critical" ? "border-[var(--accent-red)]" :
    tone === "warning" ? "border-[var(--accent-yellow)]" :
    "border-[var(--tinted-grey-200)]";
  return (
    <motion.div whileHover={{ y: -4 }} transition={{ duration: 0.2 }}
      data-testid={testid}
      className={`bg-white border ${border} p-6 h-full`}>
      <div className="flex items-start justify-between">
        <Icon size={22} weight="duotone" className="text-[var(--klein)]" />
        <span className="overline">{label}</span>
      </div>
      <div className="mt-6 font-heading font-black text-4xl tracking-tight tabular">{value}</div>
      {hint && <div className="mt-1 text-xs text-[var(--tinted-grey-500)]">{hint}</div>}
    </motion.div>
  );
}

export default function PlatformDashboardPage() {
  const [s, setS] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/platform/stats");
        setS(data);
      } catch (e) { toast.error(formatApiError(e)); }
    })();
  }, []);

  return (
    <div data-testid="platform-dashboard">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-3">Platform · Overview</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="dashboard-title">
            Every school. One console.
          </h1>
        </div>
        <Link to="/platform/schools/new">
          <button data-testid="dashboard-cta-new-school" className="rounded-full bg-[var(--klein)] hover:bg-[var(--klein-hover)] text-white transition-colors h-11 px-6 inline-flex items-center gap-2">
            <Buildings size={16} /> Onboard a school <ArrowRight size={14} />
          </button>
        </Link>
      </div>

      <div className="mt-10 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 lg:gap-6">
        <Kpi icon={Buildings} label="Total schools" value={s?.total_schools ?? "—"} testid="kpi-total" />
        <Kpi icon={CheckCircle} label="Active" value={s?.active_schools ?? "—"} testid="kpi-active" />
        <Kpi icon={Hourglass} label="Trial" value={s?.trial_schools ?? "—"} testid="kpi-trial" tone="warning" />
        <Kpi icon={Prohibit} label="Suspended" value={s?.suspended_schools ?? "—"} testid="kpi-suspended" tone="critical" />
        <Kpi icon={GraduationCap} label="Students" value={s?.total_students ?? "—"} hint="Across all tenants" testid="kpi-students" />
        <Kpi icon={ChalkboardTeacher} label="Teachers" value={s?.total_teachers ?? "—"} hint="+ class teachers" testid="kpi-teachers" />
        <Kpi icon={Coins} label="MRR" value={`$${(s?.mrr ?? 0).toLocaleString()}`} hint="Monthly recurring" testid="kpi-mrr" />
        <Kpi icon={Bell} label="Open alerts" value={s?.open_alerts ?? "—"} testid="kpi-alerts" tone={s?.open_alerts ? "warning" : "default"} />
      </div>

      {/* Recently onboarded + Subscription */}
      <div className="mt-12 grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="overline">Recently onboarded</div>
              <div className="font-heading font-bold text-xl">Latest schools</div>
            </div>
            <Link to="/platform/schools" className="klein-underline text-sm text-[var(--klein)]" data-testid="link-see-all-schools">See all →</Link>
          </div>
          <div className="bg-white border border-[var(--tinted-grey-200)] divide-y divide-[var(--tinted-grey-200)]" data-testid="recent-schools">
            {(s?.recently_onboarded || []).length === 0 && <div className="p-6 text-[var(--tinted-grey-500)] text-sm">No schools onboarded yet.</div>}
            {(s?.recently_onboarded || []).map((t) => (
              <Link key={t.id} to={`/platform/schools/${t.id}`} className="flex items-center justify-between p-4 hover:bg-[var(--tinted-grey-50)] transition-colors" data-testid={`recent-${t.slug}`}>
                <div className="min-w-0">
                  <div className="font-heading font-semibold truncate">{t.name}</div>
                  <div className="font-mono text-xs text-[var(--tinted-grey-500)]">{t.slug} · {t.school_code || "—"}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs uppercase tracking-widest text-[var(--klein)]">{t.plan}</span>
                  <StatusDot status={t.status} />
                  <ArrowRight size={14} className="text-[var(--tinted-grey-400)]" />
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="lg:col-span-4">
          <div className="mb-4">
            <div className="overline">Subscription mix</div>
            <div className="font-heading font-bold text-xl">Plans in use</div>
          </div>
          <div className="bg-white border border-[var(--tinted-grey-200)] divide-y divide-[var(--tinted-grey-200)]" data-testid="subscription-mix">
            {s && Object.entries(s.subscription_status).map(([plan, count]) => (
              <div key={plan} className="flex items-center justify-between p-4">
                <span className="uppercase tracking-widest text-xs">{plan}</span>
                <span className="font-heading font-bold tabular text-lg">{count}</span>
              </div>
            ))}
          </div>

          {s?.open_alerts > 0 && (
            <Link to="/platform/alerts" className="mt-4 flex items-center gap-2 bg-[var(--accent-yellow)] text-[var(--ink)] p-4 border border-[var(--ink)]" data-testid="dashboard-alerts-cta">
              <Warning size={18} weight="fill" />
              <span className="text-sm font-semibold">{s.open_alerts} open alert{s.open_alerts === 1 ? "" : "s"}</span>
              <ArrowRight size={14} className="ml-auto" />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusDot({ status }) {
  const color = status === "active" ? "var(--klein)" : status === "trial" ? "var(--accent-yellow)" : "var(--accent-red)";
  return (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      <span className="capitalize">{status}</span>
    </span>
  );
}
