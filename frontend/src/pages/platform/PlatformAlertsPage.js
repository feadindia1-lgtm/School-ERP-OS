import { useEffect, useState } from "react";
import { CheckCircle, Warning, Bell } from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const LEVEL_COLOR = { info: "var(--klein)", warning: "var(--accent-yellow)", critical: "var(--accent-red)" };

export default function PlatformAlertsPage() {
  const [tab, setTab] = useState("open");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/platform/alerts?unacknowledged_only=${tab === "open"}`);
      setRows(data);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [tab]);

  const ack = async (id) => {
    try {
      await api.post(`/platform/alerts/${id}/acknowledge`);
      toast.success("Acknowledged");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="alerts-page">
      <div className="overline mb-3">Alerts</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter">System alerts</h1>

      <div className="mt-8">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="rounded-none bg-transparent h-auto border-b border-[var(--tinted-grey-200)] w-full justify-start p-0">
            <TabsTrigger value="open" data-testid="alerts-tab-open" className="rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold">Open</TabsTrigger>
            <TabsTrigger value="all" data-testid="alerts-tab-all" className="rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold">All</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="mt-6 bg-white border border-[var(--tinted-grey-200)] divide-y divide-[var(--tinted-grey-200)]" data-testid="alerts-list">
        {loading && <div className="p-6 text-[var(--tinted-grey-500)]">Loading…</div>}
        {!loading && rows.length === 0 && (
          <div className="p-10 text-center">
            <CheckCircle size={28} weight="duotone" className="text-[var(--klein)] mx-auto" />
            <div className="mt-3 text-sm text-[var(--tinted-grey-500)]">All clear.</div>
          </div>
        )}
        {rows.map((a) => (
          <div key={a.id} className="p-5 flex items-start justify-between gap-4" data-testid={`alert-row-${a.id}`}>
            <div className="flex items-start gap-3 min-w-0">
              {a.level === "info" ? <Bell size={18} className="mt-0.5 shrink-0" style={{ color: LEVEL_COLOR[a.level] }} /> : <Warning size={18} weight="fill" className="mt-0.5 shrink-0" style={{ color: LEVEL_COLOR[a.level] || "var(--klein)" }} />}
              <div className="min-w-0">
                <div className="font-heading font-bold">{a.title}</div>
                <div className="text-sm text-[var(--tinted-grey-500)] mt-1 break-words">{a.message}</div>
                <div className="mt-2 font-mono text-[10px] text-[var(--tinted-grey-400)]">{new Date(a.created_at).toISOString().slice(0, 19).replace("T"," ")} · level {a.level}</div>
              </div>
            </div>
            {!a.acknowledged && (
              <Button size="sm" variant="outline" onClick={() => ack(a.id)} className="rounded-full shrink-0" data-testid={`alert-ack-${a.id}`}>Acknowledge</Button>
            )}
            {a.acknowledged && <span className="text-xs uppercase tracking-widest text-[var(--klein)] shrink-0">acked</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
