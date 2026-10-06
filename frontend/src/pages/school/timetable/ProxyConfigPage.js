/**
 * Proxy Configuration — Prompt 7.
 *
 * Admin page to tune: absence cutoff, sources (leave/attendance), ranking
 * preferences and daily proxy caps.  SMS/Email providers are reserved
 * for a later Communication prompt.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { FloppyDisk, Info } from "@phosphor-icons/react";

export default function ProxyConfigPage() {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get("/school/proxy/config");
      setCfg(data);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); }, []);

  const update = (patch) => setCfg((c) => ({ ...c, ...patch }));

  const save = async () => {
    try {
      setSaving(true);
      const payload = {
        cutoff_time: cfg.cutoff_time,
        attendance_grace_minutes: Number(cfg.attendance_grace_minutes),
        use_leave_source: !!cfg.use_leave_source,
        use_attendance_source: !!cfg.use_attendance_source,
        auto_run_enabled: !!cfg.auto_run_enabled,
        auto_run_time: cfg.auto_run_time,
        require_subject_match: !!cfg.require_subject_match,
        prefer_same_grade: !!cfg.prefer_same_grade,
        max_proxy_per_day_per_teacher: Number(cfg.max_proxy_per_day_per_teacher),
        notify_substitute: !!cfg.notify_substitute,
        notify_class_teacher: !!cfg.notify_class_teacher,
        notify_admin: !!cfg.notify_admin,
      };
      await api.put("/school/proxy/config", payload);
      toast.success("Saved");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSaving(false); }
  };

  if (!cfg) return <div className="text-xs text-[var(--tinted-grey-500)]">Loading…</div>;

  return (
    <div className="space-y-6 max-w-2xl" data-testid="proxy-config-page">
      <div className="flex items-center justify-between">
        <div>
          <div className="overline text-[10px]">Timetable</div>
          <h1 className="font-heading text-3xl font-black">Proxy Rules</h1>
          <div className="text-xs text-[var(--tinted-grey-500)]">How the system decides a teacher is absent and ranks substitutes.</div>
        </div>
        <Link to="/school/timetable/proxy" className="text-xs underline" data-testid="link-back-proxy">← Dashboard</Link>
      </div>

      <section className="space-y-3 border border-[var(--tinted-grey-200)] bg-white p-4">
        <h2 className="font-heading text-lg font-black">Absence detection</h2>
        <div className="flex items-center justify-between gap-3">
          <Label>Approved leave triggers absence</Label>
          <Switch checked={cfg.use_leave_source} onCheckedChange={(v) => update({ use_leave_source: v })} data-testid="toggle-use-leave" />
        </div>
        <div className="flex items-center justify-between gap-3">
          <Label>Unmarked attendance after cutoff triggers absence</Label>
          <Switch checked={cfg.use_attendance_source} onCheckedChange={(v) => update({ use_attendance_source: v })} data-testid="toggle-use-attendance" />
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <Label>Cutoff time (HH:MM)</Label>
            <Input value={cfg.cutoff_time} onChange={(e) => update({ cutoff_time: e.target.value })} data-testid="input-cutoff-time" />
          </div>
          <div>
            <Label>Grace minutes (late-but-present)</Label>
            <Input type="number" value={cfg.attendance_grace_minutes || 0} onChange={(e) => update({ attendance_grace_minutes: e.target.value })} data-testid="input-grace" />
          </div>
        </div>
        <div className="flex items-center justify-between gap-3">
          <Label>Auto-detect at a daily time (future)</Label>
          <Switch checked={cfg.auto_run_enabled} onCheckedChange={(v) => update({ auto_run_enabled: v })} data-testid="toggle-auto-run" />
        </div>
        {cfg.auto_run_enabled && (
          <div>
            <Label>Auto-run time</Label>
            <Input value={cfg.auto_run_time} onChange={(e) => update({ auto_run_time: e.target.value })} data-testid="input-auto-run-time" />
          </div>
        )}
      </section>

      <section className="space-y-3 border border-[var(--tinted-grey-200)] bg-white p-4">
        <h2 className="font-heading text-lg font-black">Ranking preferences</h2>
        <div className="flex items-center justify-between gap-3">
          <Label>Require subject match (hard filter)</Label>
          <Switch checked={cfg.require_subject_match} onCheckedChange={(v) => update({ require_subject_match: v })} data-testid="toggle-require-subject" />
        </div>
        <div className="flex items-center justify-between gap-3">
          <Label>Prefer same-grade teachers</Label>
          <Switch checked={cfg.prefer_same_grade} onCheckedChange={(v) => update({ prefer_same_grade: v })} data-testid="toggle-prefer-grade" />
        </div>
        <div>
          <Label>Max proxy periods per teacher per day</Label>
          <Input type="number" value={cfg.max_proxy_per_day_per_teacher} onChange={(e) => update({ max_proxy_per_day_per_teacher: e.target.value })} data-testid="input-max-proxy" />
        </div>
      </section>

      <section className="space-y-3 border border-[var(--tinted-grey-200)] bg-white p-4">
        <h2 className="font-heading text-lg font-black">In-app notifications</h2>
        <div className="text-[11px] text-[var(--tinted-grey-500)] flex items-start gap-1">
          <Info size={12} className="mt-0.5" />SMS/Email/WhatsApp come in a later Communication prompt — only in-app alerts fire today.
        </div>
        <div className="flex items-center justify-between gap-3">
          <Label>Alert the substitute</Label>
          <Switch checked={cfg.notify_substitute} onCheckedChange={(v) => update({ notify_substitute: v })} data-testid="toggle-notify-substitute" />
        </div>
        <div className="flex items-center justify-between gap-3">
          <Label>Alert the class teacher</Label>
          <Switch checked={cfg.notify_class_teacher} onCheckedChange={(v) => update({ notify_class_teacher: v })} data-testid="toggle-notify-class-teacher" />
        </div>
        <div className="flex items-center justify-between gap-3">
          <Label>Alert admin / principal</Label>
          <Switch checked={cfg.notify_admin} onCheckedChange={(v) => update({ notify_admin: v })} data-testid="toggle-notify-admin" />
        </div>
      </section>

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving} data-testid="btn-save-proxy-config"><FloppyDisk size={14} className="mr-1" />Save</Button>
      </div>
    </div>
  );
}
