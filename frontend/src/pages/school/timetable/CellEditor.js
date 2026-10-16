import { useMemo, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { FloppyDisk, Trash, Warning } from "@phosphor-icons/react";
import { WEEKDAY_LABELS } from "./_shared";

const val = (v) => (v && v !== "__none" ? v : null);

function TeacherSelect({ value, onChange, teachers, assigned }) {
  const assignedSet = new Set(assigned);
  const active = teachers.filter((t) => t.status === "active" || t.id === value);
  const top = active.filter((t) => assignedSet.has(t.id));
  const rest = active.filter((t) => !assignedSet.has(t.id));
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger data-testid="cell-teacher"><SelectValue placeholder="—" /></SelectTrigger>
      <SelectContent>
        <SelectItem value="__none" data-testid="cell-teacher-none">— None —</SelectItem>
        {top.length > 0 && (
          <SelectGroup>
            <SelectLabel className="text-[10px]">Assigned to this subject</SelectLabel>
            {top.map((t) => <SelectItem key={t.id} value={t.id} data-testid={`cell-teacher-opt-${t.id}`}>{t.full_name || t.email}</SelectItem>)}
          </SelectGroup>
        )}
        <SelectGroup>
          {top.length > 0 && <SelectLabel className="text-[10px]">Other teachers</SelectLabel>}
          {rest.map((t) => <SelectItem key={t.id} value={t.id} data-testid={`cell-teacher-opt-${t.id}`}>{t.full_name || t.email}</SelectItem>)}
        </SelectGroup>
      </SelectContent>
    </Select>
  );
}

function ConflictList({ conflicts }) {
  if (!conflicts.length) return null;
  return (
    <div className="border border-[var(--accent-red)] bg-[var(--accent-red)]/5 p-3 text-xs" data-testid="cell-conflicts">
      <div className="flex items-center gap-1 font-bold text-[var(--accent-red)] mb-2"><Warning size={12} />Conflicts</div>
      <ul className="space-y-1">{conflicts.map((c, i) => <li key={i}>• <b>{c.code}</b>: {c.message}</li>)}</ul>
    </div>
  );
}

export function CellEditor({ state, sectionId, classId, yearId, bellId, subjects, teachers, rooms, assignments, onClose, onSaved }) {
  const [subjectId, setSubjectId] = useState(state.cell?.subject_id || "");
  const [teacherId, setTeacherId] = useState(state.cell?.teacher_user_id || "");
  const [roomId, setRoomId] = useState(state.cell?.room_id || "");
  const [label, setLabel] = useState(state.cell?.label || "");
  const [conflicts, setConflicts] = useState([]);
  const [saving, setSaving] = useState(false);

  const assignedTeachers = useMemo(
    () => assignments.filter((a) => a.subject_id && a.subject_id === val(subjectId)).map((a) => a.teacher_user_id),
    [assignments, subjectId],
  );

  const onSubject = (v) => {
    setSubjectId(v);
    const match = assignments.find((a) => a.subject_id === val(v));
    if (match && !val(teacherId)) setTeacherId(match.teacher_user_id);
  };

  const save = async () => {
    try {
      setSaving(true);
      const sub = val(subjectId), tch = val(teacherId), rm = val(roomId);
      if (state.cell?.id) {
        const patch = { clear: [] };
        if (sub) patch.subject_id = sub; else patch.clear.push("subject_id");
        if (tch) patch.teacher_user_id = tch; else patch.clear.push("teacher_user_id");
        if (rm) patch.room_id = rm; else patch.clear.push("room_id");
        if (label) patch.label = label; else patch.clear.push("label");
        await api.patch(`/school/timetable/slots/${state.cell.id}`, patch);
      } else {
        await api.post("/school/timetable/slots", {
          academic_year_id: yearId, class_id: classId, section_id: sectionId,
          bell_schedule_id: bellId, weekday: state.weekday, period_no: state.period_no,
          subject_id: sub, teacher_user_id: tch, room_id: rm, label: label || null,
        });
      }
      toast.success("Saved as draft"); onSaved();
    } catch (e) {
      const detail = e?.response?.data?.error?.details || e?.response?.data?.detail;
      if (detail?.conflicts) { setConflicts(detail.conflicts); toast.error(detail.message || "Slot conflict"); }
      else toast.error(formatApiError(e));
    } finally { setSaving(false); }
  };

  const del = async () => {
    try {
      await api.delete(`/school/timetable/slots/${state.cell.id}`);
      toast.success("Deleted"); onSaved();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-md" data-testid="cell-editor-dialog">
        <DialogHeader><DialogTitle>{WEEKDAY_LABELS[state.weekday]} · Period {state.period_no}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div>
            <div className="overline text-[9px] mb-1">Subject</div>
            <Select value={subjectId} onValueChange={onSubject}>
              <SelectTrigger data-testid="cell-subject"><SelectValue placeholder="—" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none" data-testid="cell-subject-none">— None —</SelectItem>
                {subjects.map((s) => <SelectItem key={s.id} value={s.id} data-testid={`cell-subject-opt-${s.id}`}>{s.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <div className="overline text-[9px] mb-1">Teacher</div>
            <TeacherSelect value={teacherId} onChange={setTeacherId} teachers={teachers} assigned={assignedTeachers} />
            {teachers.length === 0 && (
              <div className="text-[10px] text-amber-700 mt-1" data-testid="cell-no-teachers">No teacher login accounts yet. Link staff to logins from the Staff page.</div>
            )}
          </div>
          <div>
            <div className="overline text-[9px] mb-1">Room</div>
            <Select value={roomId} onValueChange={setRoomId}>
              <SelectTrigger data-testid="cell-room"><SelectValue placeholder="—" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none" data-testid="cell-room-none">— None —</SelectItem>
                {rooms.map((r) => <SelectItem key={r.id} value={r.id} data-testid={`cell-room-opt-${r.id}`}>{r.code} — {r.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <div className="overline text-[9px] mb-1">Label (optional)</div>
            <Input value={label} onChange={(e) => setLabel(e.target.value)} data-testid="cell-label" placeholder="e.g. Assembly" />
          </div>
          <ConflictList conflicts={conflicts} />
        </div>
        <DialogFooter className="flex items-center justify-between gap-2">
          {state.cell?.id ? (
            <Button variant="outline" onClick={del} data-testid="cell-delete"><Trash size={14} className="mr-1" />Delete</Button>
          ) : <span />}
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose} data-testid="cell-cancel">Cancel</Button>
            <Button onClick={save} disabled={saving} data-testid="cell-save"><FloppyDisk size={14} className="mr-1" />Save</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
