import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash, Bell, FloppyDisk } from "@phosphor-icons/react";
import { useAcademicYears, useCurrentYear } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function BellScheduleEditorPage() {
  const { years } = useAcademicYears();
  const { yearId, setYearId, currentYear } = useCurrentYear(years);
  const readonly = currentYear?.status === "archived";
  const [schedules, setSchedules] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [selected, setSelected] = useState(null);
  const [newOpen, setNewOpen] = useState(false);
  const [newName, setNewName] = useState("Weekday");

  const load = useCallback(async () => {
    if (!yearId) return;
    try {
      const { data } = await api.get(`/school/academic/bell-schedules?academic_year_id=${yearId}`);
      setSchedules(data);
      if (data.length && !selectedId) setSelectedId(data[0].id);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [yearId, selectedId]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    setSelected(schedules.find(s => s.id === selectedId) || null);
  }, [selectedId, schedules]);

  const createSchedule = async () => {
    if (!newName.trim()) return;
    try {
      const { data } = await api.post("/school/academic/bell-schedules", {
        academic_year_id: yearId, name: newName.trim(), periods: [],
      });
      setNewOpen(false); setNewName("Weekday");
      await load(); setSelectedId(data.id);
      toast.success("Bell schedule created");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const addPeriod = () => {
    if (!selected) return;
    const nextNo = (selected.periods.length ? Math.max(...selected.periods.map(p => p.period_no)) : 0) + 1;
    const lastEnd = selected.periods[selected.periods.length - 1]?.end_time || "08:00";
    const [h, m] = lastEnd.split(":").map(Number);
    const nextStart = lastEnd;
    const endH = (h + (m + 40 >= 60 ? 1 : 0)) % 24;
    const endM = (m + 40) % 60;
    const nextEnd = `${String(endH).padStart(2,"0")}:${String(endM).padStart(2,"0")}`;
    setSelected({ ...selected, periods: [...selected.periods, { period_no: nextNo, start_time: nextStart, end_time: nextEnd, label: `P${nextNo}`, is_break: false }] });
  };
  const updatePeriod = (i, k, v) => setSelected({ ...selected, periods: selected.periods.map((p, idx) => idx === i ? { ...p, [k]: k === "period_no" ? parseInt(v || "0") : k === "is_break" ? !!v : v } : p) });
  const removePeriod = (i) => setSelected({ ...selected, periods: selected.periods.filter((_, idx) => idx !== i) });

  const savePeriods = async () => {
    if (!selected) return;
    try {
      await api.patch(`/school/academic/bell-schedules/${selected.id}`, {
        periods: selected.periods, is_default: selected.is_default,
      });
      toast.success("Schedule saved"); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const setDefault = async () => {
    if (!selected) return;
    try { await api.patch(`/school/academic/bell-schedules/${selected.id}`, { is_default: true }); toast.success("Default set"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const deleteSchedule = async () => {
    if (!selected || !window.confirm("Delete this schedule?")) return;
    try {
      await api.delete(`/school/academic/bell-schedules/${selected.id}`);
      setSelectedId(""); load(); toast.success("Deleted");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="bell-schedule-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Academic Framework</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="bell-title">Bell schedule</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Periods & breaks — used by attendance and timetable</div>
        </div>
        <div className="flex items-center gap-3">
          <Select value={yearId} onValueChange={setYearId}>
            <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="bell-year-select"><SelectValue placeholder="Year" /></SelectTrigger>
            <SelectContent>{years.map(y => <SelectItem key={y.id} value={y.id} data-testid={`bly-${y.id}`}>{y.name}{y.is_current?" (current)":""}</SelectItem>)}</SelectContent>
          </Select>
          <Dialog open={newOpen} onOpenChange={setNewOpen}>
            <DialogTrigger asChild>
              <Button disabled={!yearId || readonly} data-testid="btn-new-schedule" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> New schedule</Button>
            </DialogTrigger>
            <DialogContent className="rounded-none max-w-sm">
              <DialogHeader><DialogTitle>New bell schedule</DialogTitle></DialogHeader>
              <div><Label className="overline">Name</Label><Input value={newName} onChange={e => setNewName(e.target.value)} className={field} data-testid="bs-name" /></div>
              <DialogFooter><Button onClick={createSchedule} data-testid="bs-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {schedules.length === 0 ? (
        <div className="mt-8 bg-white border border-[var(--tinted-grey-200)] p-8 text-sm text-[var(--tinted-grey-500)]" data-testid="bell-empty">
          No bell schedules yet. Create one to define periods and breaks.
        </div>
      ) : (
        <>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Select value={selectedId} onValueChange={setSelectedId}>
              <SelectTrigger className="rounded-none h-10 w-[240px]" data-testid="bell-select"><SelectValue placeholder="Choose schedule" /></SelectTrigger>
              <SelectContent>{schedules.map(s => <SelectItem key={s.id} value={s.id} data-testid={`bs-${s.id}`}>{s.name}{s.is_default?" ★":""}</SelectItem>)}</SelectContent>
            </Select>
            {selected && !selected.is_default && (
              <Button size="sm" variant="outline" onClick={setDefault} disabled={readonly} data-testid="btn-set-default" className="rounded-none">Set default</Button>
            )}
            {selected && (
              <Button size="sm" variant="outline" onClick={deleteSchedule} disabled={readonly} data-testid="btn-del-schedule" className="rounded-none text-[var(--accent-red)]"><Trash size={12} className="mr-1"/> Delete</Button>
            )}
          </div>

          {selected && (
            <div className="mt-6 bg-white border border-[var(--tinted-grey-200)]" data-testid="bell-editor">
              <div className="p-4 border-b border-[var(--tinted-grey-200)] flex justify-between items-center">
                <div className="flex items-center gap-2 font-heading font-bold">
                  <Bell size={16} weight="duotone" className="text-[var(--klein)]"/> {selected.name} · {selected.periods.length} period{selected.periods.length === 1 ? "" : "s"}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={addPeriod} disabled={readonly} data-testid="btn-add-period" className="rounded-none bg-[var(--ink)] text-white"><Plus size={12} className="mr-1"/> Period</Button>
                  <Button size="sm" onClick={savePeriods} disabled={readonly} data-testid="btn-save-periods" className="rounded-none bg-[var(--klein)] text-white"><FloppyDisk size={12} className="mr-1"/> Save</Button>
                </div>
              </div>
              <div className="divide-y divide-[var(--tinted-grey-200)]">
                {selected.periods.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]" data-testid="periods-empty">No periods yet. Click "Period" to add.</div>}
                {selected.periods.map((p, i) => (
                  <div key={i} className="p-3 grid grid-cols-12 gap-3 items-center" data-testid={`period-row-${i}`}>
                    <Input type="number" value={p.period_no} onChange={e => updatePeriod(i, "period_no", e.target.value)} className="col-span-1 h-9 rounded-none" data-testid={`p-no-${i}`} />
                    <Input value={p.label || ""} onChange={e => updatePeriod(i, "label", e.target.value)} placeholder="Label" className="col-span-3 h-9 rounded-none" data-testid={`p-label-${i}`} />
                    <Input type="time" value={p.start_time || ""} onChange={e => updatePeriod(i, "start_time", e.target.value)} className="col-span-3 h-9 rounded-none" data-testid={`p-start-${i}`} />
                    <Input type="time" value={p.end_time || ""} onChange={e => updatePeriod(i, "end_time", e.target.value)} className="col-span-3 h-9 rounded-none" data-testid={`p-end-${i}`} />
                    <label className="col-span-1 flex items-center gap-1 text-xs">
                      <input type="checkbox" checked={!!p.is_break} onChange={e => updatePeriod(i, "is_break", e.target.checked)} data-testid={`p-break-${i}`} />
                      Break
                    </label>
                    <button onClick={() => removePeriod(i)} className="col-span-1 text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)] justify-self-end" data-testid={`p-del-${i}`}><Trash size={14}/></button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
