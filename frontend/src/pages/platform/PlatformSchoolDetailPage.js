import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, Buildings, Users, Coins, ChartLineUp, ShieldCheck, Warning, PlayCircle,
  PauseCircle, Archive, UserSwitch,
} from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/context/AuthContext";

const tabTrig = "rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold";
const field = "mt-2 h-11 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

const MODULES = [
  ["crm", "CRM"], ["attendance", "Attendance"], ["fees", "Fees"], ["payroll", "Payroll"],
  ["examinations", "Examinations"], ["curriculum", "Curriculum"], ["communication", "Communication"],
  ["ai_assistance", "AI Assistance"], ["transport", "Transport"], ["library", "Library"],
];

export default function PlatformSchoolDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [t, setT] = useState(null);
  const [usage, setUsage] = useState(null);
  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [reason, setReason] = useState("Support ticket");

  const load = async () => {
    try {
      const [tenant, u] = await Promise.all([
        api.get(`/platform/tenants/${id}`),
        api.get(`/platform/tenants/${id}/usage`),
      ]);
      setT(tenant.data);
      setUsage(u.data);
      setName(tenant.data.name);
      setContactEmail(tenant.data.contact_email);
      setPhone(tenant.data.contact?.phone || "");
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  if (!t) return <div className="text-[var(--tinted-grey-500)]">Loading school…</div>;

  const saveOverview = async () => {
    try {
      const { data } = await api.patch(`/platform/tenants/${id}`, {
        name, contact_email: contactEmail,
        contact: { ...(t.contact || {}), phone },
      });
      setT(data); toast.success("Saved");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const changeStatus = async (status) => {
    try {
      const { data } = await api.post(`/platform/tenants/${id}/status`, { status, reason });
      setT(data); toast.success(`Status → ${status}`);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const changePlan = async (plan) => {
    try {
      const { data } = await api.post(`/platform/tenants/${id}/plan`, { plan });
      setT(data); toast.success(`Plan → ${plan}`);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const toggleModule = async (k, v) => {
    try {
      const { data } = await api.post(`/platform/tenants/${id}/entitlements`, { modules: { [k]: v } });
      setT(data);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const impersonate = async () => {
    if (!reason || reason.trim().length < 4) return toast.error("Reason must be at least 4 characters");
    try {
      await api.post(`/platform/tenants/${id}/impersonate`, { reason });
      await refresh();
      toast.success("Support mode active");
      navigate("/school");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="school-detail">
      <button onClick={() => navigate("/platform/schools")} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--tinted-grey-500)] hover:text-[var(--ink)]" data-testid="back-to-schools">
        <ArrowLeft size={14} /> All schools
      </button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="overline mb-2">School · {t.slug}</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="detail-name">{t.name}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
            <span className="uppercase tracking-widest">{t.plan}</span>
            <span data-testid="detail-status" className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: t.status === "active" ? "var(--klein)" : t.status === "trial" ? "var(--accent-yellow)" : "var(--accent-red)" }} />
              <span className="capitalize">{t.status}</span>
            </span>
            <span className="font-mono">{t.school_code || "—"}</span>
            <span className="text-[var(--tinted-grey-500)]">Board · {t.board?.toUpperCase() || "—"}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2" data-testid="detail-actions">
          {t.status !== "active" && <Button data-testid="action-activate" size="sm" onClick={() => changeStatus("active")} className="rounded-full"><PlayCircle size={14} className="mr-1" /> Activate</Button>}
          {t.status !== "suspended" && <Button data-testid="action-suspend" size="sm" variant="outline" onClick={() => changeStatus("suspended")} className="rounded-full"><PauseCircle size={14} className="mr-1" /> Suspend</Button>}
          {t.status !== "archived" && <Button data-testid="action-archive" size="sm" variant="outline" onClick={() => changeStatus("archived")} className="rounded-full text-[var(--accent-red)] hover:text-[var(--accent-red)]"><Archive size={14} className="mr-1" /> Archive</Button>}
          <ImpersonateButton reason={reason} setReason={setReason} onConfirm={impersonate} />
        </div>
      </div>

      {/* KPIs */}
      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
        <MiniKpi icon={Users} label="Users" value={usage?.users_total ?? "—"} testid="detail-kpi-users" />
        <MiniKpi icon={ChartLineUp} label="Logins (30d)" value={usage?.logins_30d ?? "—"} testid="detail-kpi-logins" />
        <MiniKpi icon={ShieldCheck} label="Audit (30d)" value={usage?.audit_events_30d ?? "—"} testid="detail-kpi-audit" />
        <MiniKpi icon={Coins} label="Plan" value={t.plan} testid="detail-kpi-plan" />
      </div>

      <div className="mt-10">
        <Tabs defaultValue="overview">
          <TabsList className="rounded-none bg-transparent h-auto border-b border-[var(--tinted-grey-200)] w-full justify-start p-0">
            <TabsTrigger value="overview" className={tabTrig} data-testid="detail-tab-overview">Overview</TabsTrigger>
            <TabsTrigger value="plan" className={tabTrig} data-testid="detail-tab-plan">Plan</TabsTrigger>
            <TabsTrigger value="entitlements" className={tabTrig} data-testid="detail-tab-entitlements">Entitlements</TabsTrigger>
            <TabsTrigger value="usage" className={tabTrig} data-testid="detail-tab-usage">Usage</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-white border border-[var(--tinted-grey-200)] p-8">
              <div><Label className="overline">School name</Label><Input data-testid="edit-name" value={name} onChange={(e)=>setName(e.target.value)} className={field} /></div>
              <div><Label className="overline">Contact email</Label><Input data-testid="edit-email" value={contactEmail} onChange={(e)=>setContactEmail(e.target.value)} className={field} /></div>
              <div><Label className="overline">Phone</Label><Input data-testid="edit-phone" value={phone} onChange={(e)=>setPhone(e.target.value)} className={field} /></div>
              <div className="md:col-span-2">
                <Button data-testid="edit-save" onClick={saveOverview} className="mt-2 rounded-full bg-[var(--klein)] hover:bg-[var(--klein-hover)] text-white transition-colors">Save changes</Button>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="plan" className="mt-6">
            <div className="bg-white border border-[var(--tinted-grey-200)] p-8">
              <div className="overline mb-4">Subscription plan</div>
              <div className="flex flex-wrap items-center gap-4">
                <Select value={t.plan} onValueChange={changePlan}>
                  <SelectTrigger className="rounded-none h-11 w-[280px] border-x-0 border-t-0 border-b-2 border-[var(--ink)]" data-testid="detail-plan-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[["trial","Trial · Free"],["starter","Starter · $49/mo"],["standard","Standard · $149/mo"],["premium","Premium · $349/mo"],["enterprise","Enterprise · $899/mo"]].map(([k,l])=>(
                      <SelectItem key={k} value={k} data-testid={`detail-plan-${k}`}>{l}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {t.trial_ends_at && <div className="mt-6 text-sm text-[var(--tinted-grey-500)]">Trial ends: <span className="font-mono">{new Date(t.trial_ends_at).toISOString().slice(0, 10)}</span></div>}
            </div>
          </TabsContent>

          <TabsContent value="entitlements" className="mt-6">
            <div className="bg-white border border-[var(--tinted-grey-200)]">
              {MODULES.map(([k, label], i) => (
                <div key={k} className={`flex items-center justify-between p-4 ${i > 0 ? "border-t border-[var(--tinted-grey-200)]" : ""}`} data-testid={`entitlement-row-${k}`}>
                  <div>
                    <div className="font-heading font-semibold">{label}</div>
                    <div className="text-xs text-[var(--tinted-grey-500)] font-mono">{k}</div>
                  </div>
                  <Switch checked={!!t.modules?.[k]} onCheckedChange={(v)=>toggleModule(k, v)} data-testid={`entitlement-toggle-${k}`} />
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="usage" className="mt-6">
            <div className="bg-white border border-[var(--tinted-grey-200)] p-8">
              <div className="overline mb-4">Users by role</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="usage-by-role">
                {usage && Object.keys(usage.users_by_role || {}).length === 0 && <div className="text-sm text-[var(--tinted-grey-500)]">No users yet.</div>}
                {usage && Object.entries(usage.users_by_role).map(([role, n]) => (
                  <div key={role} className="border border-[var(--tinted-grey-200)] p-4">
                    <div className="overline">{role.replace(/_/g, " ")}</div>
                    <div className="mt-2 font-heading font-black text-2xl tabular">{n}</div>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function MiniKpi({ icon: Icon, label, value, testid }) {
  return (
    <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid={testid}>
      <div className="flex items-center justify-between">
        <Icon size={18} weight="duotone" className="text-[var(--klein)]" />
        <span className="overline">{label}</span>
      </div>
      <div className="mt-4 font-heading font-black text-2xl tabular">{value}</div>
    </div>
  );
}

function ImpersonateButton({ reason, setReason, onConfirm }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="sm" data-testid="action-impersonate" className="rounded-full bg-[var(--accent-yellow)] text-[var(--ink)] hover:bg-[var(--accent-yellow)]/80 transition-colors">
          <UserSwitch size={14} className="mr-1" /> Support mode
        </Button>
      </DialogTrigger>
      <DialogContent className="rounded-none max-w-md">
        <DialogHeader><DialogTitle className="font-heading tracking-tight flex items-center gap-2"><Warning size={20} weight="fill" className="text-[var(--accent-yellow)]" /> Enter support mode</DialogTitle></DialogHeader>
        <p className="text-sm text-[var(--tinted-grey-500)]">You will sign in as the school administrator. Every action will be attributed to you in the audit trail.</p>
        <Label className="overline mt-4">Reason (required)</Label>
        <Textarea data-testid="impersonate-reason" value={reason} onChange={(e)=>setReason(e.target.value)} className="mt-2 rounded-none focus-visible:ring-0 focus-visible:border-[var(--klein)]" rows={3} />
        <DialogFooter>
          <Button data-testid="impersonate-confirm" onClick={onConfirm} className="rounded-none bg-[var(--ink)] hover:bg-[var(--klein)] text-white transition-colors">
            Start support session
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
