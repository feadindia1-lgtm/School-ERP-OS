import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Check, X, Clock, FloppyDisk } from "@phosphor-icons/react";
import { ATTENDANCE_STATUS, STATUS_TONE } from "./_shared";

const QUICK = ["present", "absent", "late", "excused"];

export default function ClassAttendanceMarkerPage() {
  const [classes, setClasses] = useState([]);
  const [sections, setSections] = useState([]);
  const [students, setStudents] = useState([]);
  const [classId, setClassId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [marks, setMarks] = useState({});   // student_id -> status
  const [existing, setExisting] = useState({});  // student_id -> last status
  const [busy, setBusy] = useState(false);

  useEffect(() => { (async () => {
    try {
      const years = await api.get("/school/academic/years");
      const current = (years.data || []).find(y => y.is_current) || years.data?.[0];
      if (!current) return;
      const [cs, se] = await Promise.all([
        api.get(`/school/academic/classes?academic_year_id=${current.id}`),
        api.get(`/school/academic/sections?academic_year_id=${current.id}`),
      ]);
      setClasses(cs.data); setSections(se.data);
    } catch (e) { toast.error(formatApiError(e)); }
  })(); }, []);

  const loadStudents = useCallback(async () => {
    if (!classId) return;
    try {
      const cls = classes.find(c => c.id === classId);
      const q = new URLSearchParams({ page_size: "200" });
      if (cls?.name) q.set("class_name", cls.name);
      const sect = sections.find(s => s.id === sectionId);
      if (sect?.name) q.set("section", sect.name);
      const { data } = await api.get(`/school/students?${q}`);
      setStudents(data.items || []);
      // Preload existing marks
      const att = await api.get(`/school/attendance/students?date=${date}&class_id=${classId}${sectionId ? `&section_id=${sectionId}` : ""}`);
      const map = {};
      (att.data || []).forEach(a => { map[a.student_id] = a.status; });
      setExisting(map); setMarks({});
    } catch (e) { toast.error(formatApiError(e)); }
  }, [classId, sectionId, date, classes, sections]);

  useEffect(() => { loadStudents(); }, [loadStudents]);

  const setAll = (status) => {
    const m = {}; students.forEach(s => { m[s.id] = status; }); setMarks(m);
  };
  const submit = async () => {
    const entries = students.map(s => ({ student_id: s.id, status: marks[s.id] || existing[s.id] || "present" }));
    setBusy(true);
    try {
      const payload = { date, class_id: classId, entries };
      if (sectionId) payload.section_id = sectionId;
      const { data } = await api.post("/school/attendance/students/mark-class", payload);
      toast.success(`${data.accepted.length}/${data.total} saved${data.failed.length ? `, ${data.failed.length} failed` : ""}`);
      loadStudents();
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };

  const sectionsForClass = sections.filter(s => s.class_id === classId);

  return (
    <div data-testid="class-marker-page">
      <div className="overline mb-2">Attendance</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="marker-title">Class attendance</h1>
      <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Teacher bulk-mark present / absent / late / excused</div>

      <div className="mt-6 flex flex-wrap items-end gap-3">
        <div>
          <div className="overline text-[10px] mb-1">Date</div>
          <Input type="date" value={date} onChange={e => setDate(e.target.value)} className="h-10 w-[160px] rounded-none" data-testid="marker-date" />
        </div>
        <div>
          <div className="overline text-[10px] mb-1">Class</div>
          <Select value={classId} onValueChange={setClassId}>
            <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="marker-class"><SelectValue placeholder="Pick class" /></SelectTrigger>
            <SelectContent>{classes.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <div className="overline text-[10px] mb-1">Section</div>
          <Select value={sectionId || "__all"} onValueChange={v => setSectionId(v === "__all" ? "" : v)}>
            <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="marker-section"><SelectValue placeholder="(all)" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all">All sections</SelectItem>
              {sectionsForClass.map(s => <SelectItem key={s.id} value={s.id}>Section {s.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-end gap-2 ml-auto">
          <Button variant="outline" onClick={() => setAll("present")} data-testid="btn-mark-all-present" className="rounded-none"><Check size={12} className="mr-1"/> All present</Button>
          <Button variant="outline" onClick={() => setAll("absent")} data-testid="btn-mark-all-absent" className="rounded-none"><X size={12} className="mr-1"/> All absent</Button>
          <Button onClick={submit} disabled={busy || !classId || students.length === 0} data-testid="btn-save-marks" className="rounded-full bg-[var(--klein)] text-white"><FloppyDisk size={12} className="mr-1"/> Save</Button>
        </div>
      </div>

      <div className="mt-6 bg-white border border-[var(--tinted-grey-200)]" data-testid="marker-list">
        {students.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]" data-testid="marker-empty">Pick a class to load students.</div>}
        {students.map(s => {
          const cur = marks[s.id] || existing[s.id] || "present";
          return (
            <div key={s.id} className="p-3 border-b border-[var(--tinted-grey-200)] flex items-center justify-between" data-testid={`mark-row-${s.id}`}>
              <div>
                <div className="font-heading font-semibold text-sm">{s.first_name} {s.last_name || ""}</div>
                <div className="text-xs text-[var(--tinted-grey-500)]"><span className="font-mono">{s.admission_number}</span>{s.roll_number ? ` · Roll ${s.roll_number}` : ""}</div>
              </div>
              <div className="flex gap-1">
                {QUICK.map(st => (
                  <button key={st} onClick={() => setMarks(m => ({ ...m, [s.id]: st }))}
                    className={`text-[10px] uppercase tracking-widest px-2 py-1 ${cur === st ? STATUS_TONE[st] : "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]"}`}
                    data-testid={`mark-${s.id}-${st}`}>{st}</button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
