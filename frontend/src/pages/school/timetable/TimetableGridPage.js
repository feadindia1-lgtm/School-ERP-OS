import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { LockKey, LockKeyOpen, Plus, Warning, CheckCircle, ShieldCheck, Info } from "@phosphor-icons/react";
import {
  WEEKDAY_LABELS, useYearPicker, useSectionPicker,
  fetchGrid, fetchTeachers, fetchSubjects, fetchRooms,
} from "./_shared";
import { CellEditor } from "./CellEditor";

function Picker({ label, value, onChange, options, testid, placeholder }) {
  return (
    <div>
      <div className="overline text-[9px] mb-1">{label}</div>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger data-testid={testid}><SelectValue placeholder={placeholder} /></SelectTrigger>
        <SelectContent>
          {options.map((o) => <SelectItem key={o.id} value={o.id} data-testid={`${testid}-opt-${o.id}`}>{o.label}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>
  );
}

function StatusBar({ grid, onValidate, onPublish, onLock, busy }) {
  const meta = grid.meta;
  const published = meta?.status === "published";
  return (
    <div className="flex items-center justify-between flex-wrap gap-3 border-y border-[var(--tinted-grey-200)] py-3">
      <div className="flex items-center gap-2 text-xs flex-wrap">
        <Badge data-testid="tt-status-badge" className={published ? "bg-[var(--klein)] text-white" : "bg-[var(--tinted-grey-100)] text-[var(--ink)]"}>
          {published ? `published v${meta.version || 1}` : "draft"}
        </Badge>
        {meta?.has_unpublished_changes && meta?.published_at && (
          <Badge className="bg-amber-100 text-amber-700" data-testid="tt-unpublished-badge">unpublished changes</Badge>
        )}
        {meta?.locked && <Badge className="bg-amber-100 text-amber-700"><LockKey size={10} className="mr-1" />Locked</Badge>}
        <span className="text-[var(--tinted-grey-500)]">Section: <b>{grid.section?.name}</b></span>
        <span className="text-[var(--tinted-grey-500)]" data-testid="tt-slot-count">Slots: {(grid.slots || []).length}</span>
        {meta?.published_at && <span className="text-[var(--tinted-grey-500)]">Last published {new Date(meta.published_at).toLocaleString()}</span>}
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={onLock} disabled={!meta} data-testid="btn-toggle-lock">
          {meta?.locked ? <><LockKeyOpen size={14} className="mr-1" />Unlock</> : <><LockKey size={14} className="mr-1" />Lock</>}
        </Button>
        <Button variant="outline" onClick={onValidate} disabled={busy || !meta} data-testid="btn-validate-timetable">
          <ShieldCheck size={14} className="mr-1" />Validate
        </Button>
        <Button onClick={onPublish} disabled={busy || !meta || meta.locked} data-testid="btn-publish-timetable">
          <CheckCircle size={14} className="mr-1" />Publish
        </Button>
      </div>
    </div>
  );
}

function ValidationPanel({ result }) {
  if (!result) return null;
  const { errors = [], warnings = [] } = result;
  return (
    <div className={`border p-3 text-xs ${errors.length ? "border-[var(--accent-red)] bg-[var(--accent-red)]/5" : "border-emerald-600 bg-emerald-50"}`} data-testid="tt-validation-panel">
      <div className="font-bold mb-2 flex items-center gap-1" data-testid="tt-validation-summary">
        {errors.length ? <Warning size={12} className="text-[var(--accent-red)]" /> : <CheckCircle size={12} className="text-emerald-700" />}
        {errors.length ? `${errors.length} error(s) block publishing` : "No blocking errors — ready to publish"}
        {warnings.length > 0 && <span className="font-normal text-amber-700 ml-2">{warnings.length} warning(s)</span>}
      </div>
      <ul className="space-y-1">
        {errors.map((i, k) => <li key={`e${k}`} className="text-[var(--accent-red)]" data-testid={`tt-error-${i.code}`}>• {i.message}</li>)}
        {warnings.map((i, k) => <li key={`w${k}`} className="text-amber-700" data-testid={`tt-warning-${i.code}`}>• {i.message}</li>)}
      </ul>
    </div>
  );
}

function cellInfo(cell, lookups) {
  if (!cell) return null;
  return {
    subject: lookups.subjects[cell.subject_id]?.name || cell.label || null,
    teacher: lookups.teachers[cell.teacher_user_id]?.full_name || null,
    room: lookups.rooms[cell.room_id]?.code || null,
  };
}

function GridTable({ grid, lookups, issueCells, onEdit }) {
  const workingDays = grid.working_days?.length ? grid.working_days : ["mon", "tue", "wed", "thu", "fri"];
  const idx = Object.fromEntries((grid.slots || []).map((s) => [`${s.weekday}-${s.period_no}`, s]));
  return (
    <div className="overflow-x-auto border border-[var(--tinted-grey-200)] bg-white" data-testid="tt-grid-table">
      <table className="min-w-full text-xs">
        <thead>
          <tr className="bg-[var(--tinted-grey-100)]">
            <th className="p-2 text-left font-mono">Period</th>
            {workingDays.map((wd) => <th key={wd} className="p-2 text-left font-mono">{WEEKDAY_LABELS[wd]}</th>)}
          </tr>
        </thead>
        <tbody>
          {grid.bell_schedule.periods.map((p) => (
            <tr key={p.period_no} className={`border-t border-[var(--tinted-grey-200)] ${p.is_break ? "bg-amber-50/60" : ""}`} data-testid={`tt-row-${p.period_no}`}>
              <td className="p-2 font-mono bg-[var(--tinted-grey-100)]/40 whitespace-nowrap">
                <div className="font-bold">{p.label || `P${p.period_no}`}</div>
                <div className="text-[10px] text-[var(--tinted-grey-500)]">{p.start_time}–{p.end_time}</div>
              </td>
              {p.is_break ? (
                <td colSpan={workingDays.length} className="p-2 text-center text-[10px] uppercase tracking-widest text-amber-700">Break</td>
              ) : workingDays.map((wd) => {
                const key = `${wd}-${p.period_no}`;
                const cell = idx[key];
                const info = cellInfo(cell, lookups);
                const locked = grid.meta?.locked;
                return (
                  <td key={wd}
                    className={`p-2 align-top border-l border-[var(--tinted-grey-200)] transition-colors ${locked ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:bg-[var(--tinted-grey-100)]/60"} ${issueCells.has(key) ? "ring-2 ring-inset ring-[var(--accent-red)]" : ""}`}
                    onClick={() => { if (!locked) onEdit({ weekday: wd, period_no: p.period_no, cell }); }}
                    data-testid={`tt-cell-${wd}-${p.period_no}`}>
                    {!info ? (
                      <div className="text-[var(--tinted-grey-500)] text-[10px] flex items-center gap-1"><Plus size={10} />Add</div>
                    ) : (
                      <div className="space-y-0.5">
                        {info.subject && <div className="font-bold">{info.subject}</div>}
                        {info.teacher && <div className="text-[var(--tinted-grey-500)]">{info.teacher}</div>}
                        {info.room && <div className="text-[10px] font-mono">{info.room}</div>}
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function useLookups() {
  const [data, setData] = useState({ teachers: [], subjects: [], rooms: [] });
  useEffect(() => {
    (async () => {
      try {
        const [teachers, subjects, rooms] = await Promise.all([fetchTeachers(), fetchSubjects(), fetchRooms()]);
        setData({ teachers, subjects, rooms });
      } catch (e) { toast.error(formatApiError(e)); }
    })();
  }, []);
  return data;
}

function EmptyNote({ testid, children }) {
  return (
    <div className="text-sm text-[var(--tinted-grey-500)] py-8 flex items-start gap-2" data-testid={testid}>
      <Info size={16} className="mt-0.5 shrink-0" /><div>{children}</div>
    </div>
  );
}

export default function TimetableGridPage() {
  const { years, yearId, setYearId } = useYearPicker();
  const { classes, sectionsForClass, classId, setClassId, sectionId, setSectionId } = useSectionPicker(yearId);
  const { teachers, subjects, rooms } = useLookups();
  const [grid, setGrid] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(null);
  const [bellSchedules, setBellSchedules] = useState([]);
  const [validation, setValidation] = useState(null);

  useEffect(() => {
    if (!yearId) return;
    api.get("/school/academic/bell-schedules", { params: { academic_year_id: yearId } })
      .then(({ data }) => setBellSchedules(data)).catch((e) => toast.error(formatApiError(e)));
  }, [yearId]);

  const loadGrid = async () => {
    if (!yearId || !sectionId) { setGrid(null); return; }
    try {
      setLoading(true);
      setGrid(await fetchGrid(yearId, sectionId));
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { setValidation(null); loadGrid(); /* eslint-disable-next-line */ }, [yearId, sectionId]);

  const lookups = useMemo(() => ({
    subjects: Object.fromEntries(subjects.map((s) => [s.id, s])),
    teachers: Object.fromEntries(teachers.map((t) => [t.id, t])),
    rooms: Object.fromEntries(rooms.map((r) => [r.id, r])),
  }), [subjects, teachers, rooms]);

  const issueCells = useMemo(() => new Set((validation?.errors || []).filter((i) => i.weekday).map((i) => `${i.weekday}-${i.period_no}`)), [validation]);
  const bellId = grid?.bell_schedule?.id || "";
  const body = { academic_year_id: yearId, section_id: sectionId };

  const changeBell = async (id) => {
    try {
      await api.post("/school/timetable/sections/bell", { ...body, class_id: classId, bell_schedule_id: id });
      toast.success("Bell schedule applied to this section"); loadGrid();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const ensureMeta = async () => {
    if (grid?.meta || !bellId) return;
    await api.post("/school/timetable/sections/bell", { ...body, class_id: classId, bell_schedule_id: bellId });
  };

  const validate = async () => {
    try { setBusy(true); const { data } = await api.post("/school/timetable/sections/validate", body); setValidation(data); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };

  const publish = async () => {
    try {
      setBusy(true);
      await api.post("/school/timetable/sections/publish", body);
      toast.success("Timetable published"); setValidation(null); loadGrid();
    } catch (e) {
      const d = e?.response?.data?.error?.details || e?.response?.data?.detail;
      if (d?.errors) setValidation({ errors: d.errors, warnings: d.warnings || [] });
      toast.error(formatApiError(e));
    } finally { setBusy(false); }
  };

  const toggleLock = async () => {
    try {
      await api.post("/school/timetable/sections/lock", { ...body, locked: !grid.meta.locked });
      toast.success(grid.meta.locked ? "Unlocked" : "Locked"); loadGrid();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const openEditor = async (st) => {
    try { await ensureMeta(); setEditing(st); } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="space-y-6" data-testid="timetable-grid-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="overline text-[10px]">Timetable</div>
          <h1 className="font-heading text-3xl font-black" data-testid="timetable-grid-title">Master Grid</h1>
          <div className="text-xs text-[var(--tinted-grey-500)]">Edit as a draft, validate for conflicts, then publish.</div>
        </div>
        <div className="flex gap-3 flex-wrap">
          <Link to="/school/timetable/proxy" className="text-xs underline" data-testid="link-to-proxy">Proxy & Substitutes →</Link>
          <Link to="/school/timetable/proxy-config" className="text-xs underline" data-testid="link-to-proxy-config">Proxy Settings →</Link>
        </div>
      </div>

      <div className="grid md:grid-cols-4 gap-3">
        <Picker label="Academic year" value={yearId} onChange={setYearId} testid="year-picker" placeholder="Pick year"
          options={years.map((y) => ({ id: y.id, label: y.name }))} />
        <Picker label="Class" value={classId} onChange={(v) => { setClassId(v); setSectionId(""); }} testid="class-picker" placeholder="Pick class"
          options={classes.map((c) => ({ id: c.id, label: c.name }))} />
        <Picker label="Section" value={sectionId} onChange={setSectionId} testid="section-picker" placeholder="Pick section"
          options={sectionsForClass.map((s) => ({ id: s.id, label: s.name }))} />
        <Picker label="Bell schedule" value={bellId} onChange={changeBell} testid="bell-picker" placeholder="No bell schedule"
          options={bellSchedules.map((b) => ({ id: b.id, label: `${b.name}${b.is_default ? " (default)" : ""}` }))} />
      </div>

      {grid?.bell_schedule && <StatusBar grid={grid} onValidate={validate} onPublish={publish} onLock={toggleLock} busy={busy} />}
      <ValidationPanel result={validation} />

      {!sectionId ? (
        <EmptyNote testid="tt-pick-section">Pick a class and section to see its timetable.</EmptyNote>
      ) : loading || !grid ? (
        <div className="text-sm text-[var(--tinted-grey-500)]">Loading…</div>
      ) : !grid.bell_schedule ? (
        <EmptyNote testid="tt-no-bell">No bell schedule exists for this academic year. <Link className="underline" to="/school/academic/bell-schedule">Create one</Link> to define periods.</EmptyNote>
      ) : !grid.bell_schedule.periods?.length ? (
        <EmptyNote testid="tt-no-periods">Bell schedule “{grid.bell_schedule.name}” has no periods. <Link className="underline" to="/school/academic/bell-schedule">Add periods</Link>.</EmptyNote>
      ) : (
        <GridTable grid={grid} lookups={lookups} issueCells={issueCells} onEdit={openEditor} />
      )}

      {editing && (
        <CellEditor state={editing} sectionId={sectionId} classId={classId} yearId={yearId} bellId={bellId}
          subjects={subjects} teachers={teachers} rooms={rooms} assignments={grid?.teacher_assignments || []}
          onClose={() => setEditing(null)} onSaved={() => { setEditing(null); setValidation(null); loadGrid(); }} />
      )}
    </div>
  );
}
