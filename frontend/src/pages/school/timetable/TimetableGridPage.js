/**
 * Timetable grid editor — Prompt 7.
 *
 * Shows one section's weekly timetable as a weekday × period grid.  Each
 * cell can be clicked to edit the subject, teacher and room.  Conflicts
 * (teacher double-book, room double-book) are surfaced on save.
 */
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { LockKey, LockKeyOpen, FloppyDisk, Trash, Plus, Warning, CheckCircle, Users } from "@phosphor-icons/react";
import {
  WEEKDAY_LABELS, useYearPicker, useSectionPicker,
  fetchGrid, fetchTeachers, fetchSubjects, fetchRooms,
} from "./_shared";

function cellLabel(cell, subjectsById, teachersById, roomsById) {
  if (!cell) return { empty: true };
  const subject = subjectsById[cell.subject_id];
  const teacher = teachersById[cell.teacher_user_id];
  const room = roomsById[cell.room_id];
  return {
    subject: subject ? `${subject.name}` : (cell.label || null),
    teacher: teacher ? (teacher.full_name || teacher.email) : null,
    room: room ? room.code : null,
  };
}

export default function TimetableGridPage() {
  const { years, yearId, setYearId } = useYearPicker();
  const { classes, sectionsForClass, classId, setClassId, sectionId, setSectionId } = useSectionPicker(yearId);
  const [grid, setGrid] = useState(null);
  const [loading, setLoading] = useState(false);
  const [teachers, setTeachers] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [editing, setEditing] = useState(null);   // { weekday, period_no, cell|null }
  const [bellId, setBellId] = useState("");
  const [bellSchedules, setBellSchedules] = useState([]);

  // Load lookups
  useEffect(() => { (async () => {
    try {
      setTeachers(await fetchTeachers());
      setSubjects(await fetchSubjects());
      setRooms(await fetchRooms());
    } catch (e) { toast.error(formatApiError(e)); }
  })(); }, []);

  // Load bell schedules for year
  useEffect(() => { (async () => {
    if (!yearId) return;
    try {
      const { data } = await api.get("/school/academic/bell-schedules", { params: { academic_year_id: yearId } });
      setBellSchedules(data);
      const def = data.find((b) => b.is_default) || data[0];
      if (def) setBellId(def.id);
    } catch (e) { toast.error(formatApiError(e)); }
  })(); }, [yearId]);

  const loadGrid = async () => {
    if (!yearId || !sectionId) return;
    try {
      setLoading(true);
      const data = await fetchGrid(yearId, sectionId);
      setGrid(data);
      if (data.bell_schedule?.id) setBellId(data.bell_schedule.id);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { loadGrid(); /* eslint-disable-next-line */ }, [yearId, sectionId]);

  const subjectsById = useMemo(() => Object.fromEntries(subjects.map((s) => [s.id, s])), [subjects]);
  const teachersById = useMemo(() => Object.fromEntries(teachers.map((t) => [t.id, t])), [teachers]);
  const roomsById = useMemo(() => Object.fromEntries(rooms.map((r) => [r.id, r])), [rooms]);

  // Build an index: { `${weekday}-${period_no}`: slot }
  const cellIdx = useMemo(() => {
    const idx = {};
    (grid?.slots || []).forEach((s) => { idx[`${s.weekday}-${s.period_no}`] = s; });
    return idx;
  }, [grid]);

  const workingDays = grid?.working_days?.length ? grid.working_days : ["mon", "tue", "wed", "thu", "fri"];
  const periods = (grid?.bell_schedule?.periods || []).sort((a, b) => a.period_no - b.period_no);

  const toggleLock = async () => {
    if (!grid?.meta) { toast.error("Add at least one slot to initialise the timetable first"); return; }
    try {
      await api.post("/school/timetable/sections/lock", {
        academic_year_id: yearId, section_id: sectionId, locked: !grid.meta.locked,
      });
      toast.success(grid.meta.locked ? "Unlocked" : "Locked");
      loadGrid();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const publish = async () => {
    try {
      await api.post("/school/timetable/sections/publish", {
        academic_year_id: yearId, section_id: sectionId,
      });
      toast.success("Timetable published");
      loadGrid();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="space-y-6" data-testid="timetable-grid-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="overline text-[10px]">Timetable</div>
          <h1 className="font-heading text-3xl font-black" data-testid="timetable-grid-title">Master Grid</h1>
          <div className="text-xs text-[var(--tinted-grey-500)]">Edit a section's weekly timetable. Conflicts are detected on save.</div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link to="/school/timetable/proxy" className="text-xs underline" data-testid="link-to-proxy">Proxy & Substitutes →</Link>
          <Link to="/school/timetable/proxy-config" className="text-xs underline" data-testid="link-to-proxy-config">Proxy Settings →</Link>
        </div>
      </div>

      {/* Pickers */}
      <div className="grid md:grid-cols-4 gap-3">
        <div>
          <div className="overline text-[9px] mb-1">Academic year</div>
          <Select value={yearId} onValueChange={setYearId}>
            <SelectTrigger data-testid="year-picker"><SelectValue placeholder="Pick year" /></SelectTrigger>
            <SelectContent>
              {years.map((y) => <SelectItem key={y.id} value={y.id} data-testid={`year-opt-${y.id}`}>{y.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div>
          <div className="overline text-[9px] mb-1">Class</div>
          <Select value={classId} onValueChange={setClassId}>
            <SelectTrigger data-testid="class-picker"><SelectValue placeholder="Pick class" /></SelectTrigger>
            <SelectContent>
              {classes.map((c) => <SelectItem key={c.id} value={c.id} data-testid={`cls-opt-${c.id}`}>{c.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div>
          <div className="overline text-[9px] mb-1">Section</div>
          <Select value={sectionId} onValueChange={setSectionId}>
            <SelectTrigger data-testid="section-picker"><SelectValue placeholder="Pick section" /></SelectTrigger>
            <SelectContent>
              {sectionsForClass.map((s) => <SelectItem key={s.id} value={s.id} data-testid={`sec-opt-${s.id}`}>{s.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div>
          <div className="overline text-[9px] mb-1">Bell schedule</div>
          <Select value={bellId} onValueChange={setBellId}>
            <SelectTrigger data-testid="bell-picker"><SelectValue placeholder="Default" /></SelectTrigger>
            <SelectContent>
              {bellSchedules.map((b) => <SelectItem key={b.id} value={b.id} data-testid={`bell-opt-${b.id}`}>{b.name}{b.is_default ? " (default)" : ""}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Toolbar */}
      {grid && (
        <div className="flex items-center justify-between flex-wrap gap-3 border-y border-[var(--tinted-grey-200)] py-3">
          <div className="flex items-center gap-2 text-xs">
            <Badge data-testid="tt-status-badge" className={grid.meta?.status === "published" ? "bg-[var(--klein)] text-white" : "bg-[var(--tinted-grey-100)]"}>
              {grid.meta?.status || "draft"}
            </Badge>
            {grid.meta?.locked ? (
              <Badge className="bg-amber-100 text-amber-700"><LockKey size={10} className="mr-1" />Locked</Badge>
            ) : null}
            <span className="text-[var(--tinted-grey-500)]">Section: <b>{grid.section?.name}</b></span>
            <span className="text-[var(--tinted-grey-500)]">Slots: {(grid.slots || []).length}</span>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={toggleLock} data-testid="btn-toggle-lock">
              {grid.meta?.locked ? <><LockKeyOpen size={14} className="mr-1" />Unlock</> : <><LockKey size={14} className="mr-1" />Lock</>}
            </Button>
            <Button onClick={publish} data-testid="btn-publish-timetable" disabled={!grid.meta || grid.meta.locked}>
              <CheckCircle size={14} className="mr-1" />Publish
            </Button>
          </div>
        </div>
      )}

      {/* Grid */}
      {!sectionId ? (
        <div className="text-sm text-[var(--tinted-grey-500)] py-8" data-testid="tt-pick-section">Pick a class and section to see its timetable.</div>
      ) : loading ? (
        <div className="text-sm text-[var(--tinted-grey-500)]">Loading…</div>
      ) : (
        <div className="overflow-x-auto border border-[var(--tinted-grey-200)] bg-white" data-testid="tt-grid-table">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="bg-[var(--tinted-grey-100)]">
                <th className="p-2 text-left font-mono">Period</th>
                {workingDays.map((wd) => (
                  <th key={wd} className="p-2 text-left font-mono">{WEEKDAY_LABELS[wd]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {periods.map((p) => (
                <tr key={p.period_no} className="border-t border-[var(--tinted-grey-200)]">
                  <td className="p-2 font-mono bg-[var(--tinted-grey-100)]/40">
                    <div className="font-bold">P{p.period_no}</div>
                    <div className="text-[10px] text-[var(--tinted-grey-500)]">{p.start_time}–{p.end_time}</div>
                    {p.is_break && <div className="text-[10px] text-amber-700">Break</div>}
                  </td>
                  {workingDays.map((wd) => {
                    const cell = cellIdx[`${wd}-${p.period_no}`];
                    const info = cellLabel(cell, subjectsById, teachersById, roomsById);
                    const disabled = p.is_break || grid?.meta?.locked;
                    return (
                      <td
                        key={wd}
                        className={`p-2 align-top border-l border-[var(--tinted-grey-200)] cursor-pointer hover:bg-[var(--tinted-grey-100)]/50 ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
                        onClick={() => { if (!disabled) setEditing({ weekday: wd, period_no: p.period_no, cell }); }}
                        data-testid={`tt-cell-${wd}-${p.period_no}`}
                      >
                        {info.empty ? (
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
      )}

      {editing && (
        <CellEditor
          state={editing}
          sectionId={sectionId}
          classId={classId}
          yearId={yearId}
          bellId={bellId}
          subjects={subjects}
          teachers={teachers}
          rooms={rooms}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); loadGrid(); }}
        />
      )}
    </div>
  );
}


function CellEditor({ state, sectionId, classId, yearId, bellId, subjects, teachers, rooms, onClose, onSaved }) {
  const [subjectId, setSubjectId] = useState(state.cell?.subject_id || "");
  const [teacherId, setTeacherId] = useState(state.cell?.teacher_user_id || "");
  const [roomId, setRoomId] = useState(state.cell?.room_id || "");
  const [label, setLabel] = useState(state.cell?.label || "");
  const [conflicts, setConflicts] = useState([]);
  const [saving, setSaving] = useState(false);

  const basePayload = {
    academic_year_id: yearId, class_id: classId, section_id: sectionId,
    bell_schedule_id: bellId, weekday: state.weekday, period_no: state.period_no,
  };

  const save = async () => {
    try {
      setSaving(true);
      const sub = (subjectId && subjectId !== "__none") ? subjectId : null;
      const tch = (teacherId && teacherId !== "__none") ? teacherId : null;
      const rm = (roomId && roomId !== "__none") ? roomId : null;
      if (state.cell?.id) {
        const patch = { clear: [] };
        if (sub) patch.subject_id = sub; else patch.clear.push("subject_id");
        if (tch) patch.teacher_user_id = tch; else patch.clear.push("teacher_user_id");
        if (rm) patch.room_id = rm; else patch.clear.push("room_id");
        if (label) patch.label = label; else patch.clear.push("label");
        await api.patch(`/school/timetable/slots/${state.cell.id}`, patch);
      } else {
        await api.post("/school/timetable/slots", {
          ...basePayload,
          subject_id: sub, teacher_user_id: tch, room_id: rm, label: label || null,
        });
      }
      toast.success("Saved"); onSaved();
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.response?.data?.error?.details;
      if (detail?.conflicts) {
        setConflicts(detail.conflicts);
        toast.error(detail.message || "Slot conflict");
      } else {
        toast.error(formatApiError(e));
      }
    } finally { setSaving(false); }
  };

  const del = async () => {
    if (!state.cell?.id) return;
    try {
      await api.delete(`/school/timetable/slots/${state.cell.id}`);
      toast.success("Deleted"); onSaved();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-md" data-testid="cell-editor-dialog">
        <DialogHeader>
          <DialogTitle>{WEEKDAY_LABELS[state.weekday]} · Period {state.period_no}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <div className="overline text-[9px] mb-1">Subject</div>
            <Select value={subjectId} onValueChange={setSubjectId}>
              <SelectTrigger data-testid="cell-subject"><SelectValue placeholder="—" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none" data-testid="cell-subject-none">— None —</SelectItem>
                {subjects.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <div className="overline text-[9px] mb-1">Teacher</div>
            <Select value={teacherId} onValueChange={setTeacherId}>
              <SelectTrigger data-testid="cell-teacher"><SelectValue placeholder="—" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none" data-testid="cell-teacher-none">— None —</SelectItem>
                {teachers.map((t) => <SelectItem key={t.id} value={t.id}>{t.full_name || t.email}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <div className="overline text-[9px] mb-1">Room</div>
            <Select value={roomId} onValueChange={setRoomId}>
              <SelectTrigger data-testid="cell-room"><SelectValue placeholder="—" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none" data-testid="cell-room-none">— None —</SelectItem>
                {rooms.map((r) => <SelectItem key={r.id} value={r.id}>{r.code} — {r.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <div className="overline text-[9px] mb-1">Label (optional)</div>
            <Input value={label} onChange={(e) => setLabel(e.target.value)} data-testid="cell-label" placeholder="e.g. Assembly" />
          </div>

          {conflicts.length > 0 && (
            <div className="border border-[var(--accent-red)] bg-[var(--accent-red)]/5 p-3 text-xs" data-testid="cell-conflicts">
              <div className="flex items-center gap-1 font-bold text-[var(--accent-red)] mb-2"><Warning size={12} />Conflicts</div>
              <ul className="space-y-1">
                {conflicts.map((c, i) => (
                  <li key={i}>• <b>{c.code}</b>: {c.message}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <DialogFooter className="flex items-center justify-between gap-2">
          {state.cell?.id ? (
            <Button variant="outline" onClick={del} data-testid="cell-delete"><Trash size={14} className="mr-1" />Delete</Button>
          ) : <span />}
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose} data-testid="cell-cancel">Cancel</Button>
            <Button onClick={save} disabled={saving} data-testid="cell-save">
              <FloppyDisk size={14} className="mr-1" />Save
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
