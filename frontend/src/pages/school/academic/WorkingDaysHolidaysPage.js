import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash, Calendar as CalIcon, FloppyDisk } from "@phosphor-icons/react";
import { useAcademicYears, useCurrentYear, WEEKDAYS, WEEKDAY_LABELS } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";
const HOLIDAY_CATEGORIES = ["public", "school", "optional", "exam"];

export default function WorkingDaysHolidaysPage() {
  const { years } = useAcademicYears();
  const { yearId, setYearId, currentYear } = useCurrentYear(years);
  const readonly = currentYear?.status === "archived";
  const [policy, setPolicy] = useState(null);
  const [holidays, setHolidays] = useState([]);
  const [holOpen, setHolOpen] = useState(false);
  const [holForm, setHolForm] = useState({ name: "", start_date: "", end_date: "", category: "public", is_recurring: false, notes: "" });

  const load = useCallback(async () => {
    if (!yearId) return;
    try {
      const [p, h] = await Promise.all([
        api.get(`/school/academic/working-day-policy?academic_year_id=${yearId}`),
        api.get(`/school/academic/holidays?academic_year_id=${yearId}`),
      ]);
      setPolicy(p.data); setHolidays(h.data);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [yearId]);
  useEffect(() => { load(); }, [load]);

  const toggleDay = (day, target) => {
    if (!policy) return;
    const next = { ...policy };
    ["working_days", "half_days", "weekly_off"].forEach(k => { next[k] = next[k] || []; });
    if (target === "working_days") {
      // Ensure removed from weekly_off if added
      if (next.working_days.includes(day)) next.working_days = next.working_days.filter(d => d !== day);
      else { next.working_days = [...next.working_days, day]; next.weekly_off = next.weekly_off.filter(d => d !== day); }
    } else if (target === "weekly_off") {
      if (next.weekly_off.includes(day)) next.weekly_off = next.weekly_off.filter(d => d !== day);
      else { next.weekly_off = [...next.weekly_off, day]; next.working_days = next.working_days.filter(d => d !== day); }
    } else if (target === "half_days") {
      if (next.half_days.includes(day)) next.half_days = next.half_days.filter(d => d !== day);
      else next.half_days = [...next.half_days, day];
    }
    setPolicy(next);
  };
  const savePolicy = async () => {
    try {
      await api.put(`/school/academic/working-day-policy`, {
        academic_year_id: yearId, working_days: policy.working_days || [],
        half_days: policy.half_days || [], weekly_off: policy.weekly_off || [],
        notes: policy.notes || null,
      });
      toast.success("Working-day policy saved"); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const createHoliday = async () => {
    if (!holForm.name || !holForm.start_date || !holForm.end_date) return toast.error("Fill all required fields");
    try {
      await api.post("/school/academic/holidays", { ...holForm, academic_year_id: yearId });
      toast.success("Holiday added"); setHolOpen(false);
      setHolForm({ name: "", start_date: "", end_date: "", category: "public", is_recurring: false, notes: "" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const deleteHoliday = async (id) => {
    if (!window.confirm("Delete this holiday?")) return;
    try { await api.delete(`/school/academic/holidays/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="working-days-holidays-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Academic Framework</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="wdh-title">School calendar</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Working days & holidays for the selected year</div>
        </div>
        <Select value={yearId} onValueChange={setYearId}>
          <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="wdh-year-select"><SelectValue placeholder="Year" /></SelectTrigger>
          <SelectContent>{years.map(y => <SelectItem key={y.id} value={y.id} data-testid={`wdhy-${y.id}`}>{y.name}{y.is_current?" (current)":""}</SelectItem>)}</SelectContent>
        </Select>
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Working days card */}
        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="policy-card">
          <div className="flex items-center justify-between mb-4">
            <div className="overline">Working days</div>
            <Button size="sm" onClick={savePolicy} disabled={readonly || !policy} data-testid="btn-save-policy" className="rounded-none bg-[var(--klein)] text-white"><FloppyDisk size={12} className="mr-1"/> Save</Button>
          </div>
          {policy && (
            <div className="space-y-4">
              <div>
                <div className="text-xs text-[var(--tinted-grey-500)] mb-2">Weekly on</div>
                <div className="flex flex-wrap gap-2">
                  {WEEKDAYS.map(d => (
                    <button key={d} disabled={readonly} onClick={() => toggleDay(d, "working_days")} data-testid={`wd-${d}`} className={`h-9 w-12 text-xs uppercase tracking-widest ${policy.working_days?.includes(d) ? "bg-[var(--klein)] text-white" : "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]"}`}>
                      {WEEKDAY_LABELS[d]}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--tinted-grey-500)] mb-2">Weekly off</div>
                <div className="flex flex-wrap gap-2">
                  {WEEKDAYS.map(d => (
                    <button key={d} disabled={readonly} onClick={() => toggleDay(d, "weekly_off")} data-testid={`wo-${d}`} className={`h-9 w-12 text-xs uppercase tracking-widest ${policy.weekly_off?.includes(d) ? "bg-[var(--tinted-grey-500)] text-white" : "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]"}`}>
                      {WEEKDAY_LABELS[d]}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--tinted-grey-500)] mb-2">Half days (subset of working days)</div>
                <div className="flex flex-wrap gap-2">
                  {WEEKDAYS.filter(d => policy.working_days?.includes(d)).map(d => (
                    <button key={d} disabled={readonly} onClick={() => toggleDay(d, "half_days")} data-testid={`hd-${d}`} className={`h-9 w-12 text-xs uppercase tracking-widest ${policy.half_days?.includes(d) ? "bg-[var(--accent-yellow)] text-[var(--ink)]" : "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]"}`}>
                      {WEEKDAY_LABELS[d]}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <Label className="overline">Notes</Label>
                <Input value={policy.notes || ""} onChange={e => setPolicy({ ...policy, notes: e.target.value })} className={field} data-testid="wd-notes" />
              </div>
            </div>
          )}
        </div>

        {/* Holidays card */}
        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="holidays-card">
          <div className="flex items-center justify-between mb-4">
            <div className="overline">Holidays ({holidays.length})</div>
            <Dialog open={holOpen} onOpenChange={setHolOpen}>
              <DialogTrigger asChild>
                <Button size="sm" disabled={readonly || !yearId} data-testid="btn-new-holiday" className="rounded-none bg-[var(--klein)] text-white"><Plus size={12} className="mr-1"/> Add</Button>
              </DialogTrigger>
              <DialogContent className="rounded-none max-w-md">
                <DialogHeader><DialogTitle>New holiday</DialogTitle></DialogHeader>
                <div className="space-y-4">
                  <div><Label className="overline">Name</Label><Input value={holForm.name} onChange={e => setHolForm({ ...holForm, name: e.target.value })} className={field} data-testid="hl-name" /></div>
                  <div className="grid grid-cols-2 gap-4">
                    <div><Label className="overline">Start</Label><Input type="date" value={holForm.start_date} onChange={e => setHolForm({ ...holForm, start_date: e.target.value })} className={field} data-testid="hl-start" /></div>
                    <div><Label className="overline">End</Label><Input type="date" value={holForm.end_date} onChange={e => setHolForm({ ...holForm, end_date: e.target.value })} className={field} data-testid="hl-end" /></div>
                  </div>
                  <div><Label className="overline">Category</Label>
                    <Select value={holForm.category} onValueChange={v => setHolForm({ ...holForm, category: v })}>
                      <SelectTrigger className="rounded-none h-10 mt-2" data-testid="hl-cat"><SelectValue /></SelectTrigger>
                      <SelectContent>{HOLIDAY_CATEGORIES.map(c => <SelectItem key={c} value={c} data-testid={`hlc-${c}`}>{c}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={holForm.is_recurring} onChange={e => setHolForm({ ...holForm, is_recurring: e.target.checked })} data-testid="hl-recurring" /> Recurring every year
                  </label>
                  <div><Label className="overline">Notes</Label><Input value={holForm.notes} onChange={e => setHolForm({ ...holForm, notes: e.target.value })} className={field} data-testid="hl-notes" /></div>
                </div>
                <DialogFooter><Button onClick={createHoliday} data-testid="hl-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="divide-y divide-[var(--tinted-grey-200)] -mx-2 max-h-[440px] overflow-y-auto" data-testid="holidays-list">
            {holidays.length === 0 && <div className="p-4 text-sm text-[var(--tinted-grey-500)]" data-testid="hol-empty">No holidays yet.</div>}
            {holidays.map(h => (
              <div key={h.id} className="px-2 py-3 flex items-start justify-between" data-testid={`hol-row-${h.id}`}>
                <div className="flex items-start gap-3">
                  <CalIcon size={16} weight="duotone" className="text-[var(--klein)] mt-0.5"/>
                  <div>
                    <div className="font-heading font-semibold text-sm">{h.name}</div>
                    <div className="text-xs text-[var(--tinted-grey-500)]">
                      {h.start_date?.slice(0,10)}{h.start_date !== h.end_date ? ` → ${h.end_date?.slice(0,10)}` : ""} · <span className="capitalize">{h.category}</span>{h.is_recurring ? " · recurring" : ""}
                    </div>
                  </div>
                </div>
                <button onClick={() => deleteHoliday(h.id)} disabled={readonly} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)] disabled:opacity-30" data-testid={`btn-del-hol-${h.id}`}><Trash size={14}/></button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
