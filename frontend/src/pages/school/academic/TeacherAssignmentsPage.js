import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash, ChalkboardTeacher, Star } from "@phosphor-icons/react";
import { useAcademicYears, useCurrentYear } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function TeacherAssignmentsPage() {
  const { years } = useAcademicYears();
  const { yearId, setYearId, currentYear } = useCurrentYear(years);
  const readonly = currentYear?.status === "archived";
  const [assignments, setAssignments] = useState([]);
  const [classes, setClasses] = useState([]);
  const [sections, setSections] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ teacher_user_id: "", class_id: "", section_id: "", subject_id: "", is_class_teacher: false, weekly_periods: 0 });
  const [filterClass, setFilterClass] = useState("");

  const load = useCallback(async () => {
    if (!yearId) return;
    try {
      const [a, c, se, su, u] = await Promise.all([
        api.get(`/school/academic/teacher-assignments?academic_year_id=${yearId}${filterClass ? `&class_id=${filterClass}` : ""}`),
        api.get(`/school/academic/classes?academic_year_id=${yearId}`),
        api.get(`/school/academic/sections?academic_year_id=${yearId}`),
        api.get(`/school/academic/subjects`),
        api.get(`/school/users`),
      ]);
      setAssignments(a.data); setClasses(c.data); setSections(se.data); setSubjects(su.data);
      setTeachers((u.data || []).filter(x => ["teacher", "class_teacher"].includes(x.role)));
    } catch (e) { toast.error(formatApiError(e)); }
  }, [yearId, filterClass]);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    if (!form.teacher_user_id || !form.class_id) return toast.error("Teacher & class required");
    try {
      const payload = { ...form, academic_year_id: yearId };
      Object.keys(payload).forEach(k => (payload[k] === "" || payload[k] === 0) && delete payload[k]);
      // is_class_teacher is boolean — keep it explicitly
      payload.is_class_teacher = !!form.is_class_teacher;
      await api.post("/school/academic/teacher-assignments", payload);
      toast.success("Assignment created"); setOpen(false);
      setForm({ teacher_user_id: "", class_id: "", section_id: "", subject_id: "", is_class_teacher: false, weekly_periods: 0 });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const del = async (id) => {
    if (!window.confirm("Delete this assignment?")) return;
    try { await api.delete(`/school/academic/teacher-assignments/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const teacherName = (id) => { const t = teachers.find(x => x.id === id); return t ? (t.full_name || t.email) : "—"; };
  const className = (id) => classes.find(c => c.id === id)?.name || "—";
  const sectionName = (id) => sections.find(s => s.id === id)?.name || "";
  const subjectName = (id) => subjects.find(s => s.id === id)?.name || (id ? "?" : "Class-teacher");

  const sectionsForForm = sections.filter(s => s.class_id === form.class_id);

  return (
    <div data-testid="teacher-assignments-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Academic Framework</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="ta-title">Teacher assignments</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{assignments.length} assignment{assignments.length === 1 ? "" : "s"} · powering attendance & timetable</div>
        </div>
        <div className="flex items-center gap-3">
          <Select value={yearId} onValueChange={setYearId}>
            <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="ta-year-select"><SelectValue placeholder="Year" /></SelectTrigger>
            <SelectContent>{years.map(y => <SelectItem key={y.id} value={y.id} data-testid={`tay-${y.id}`}>{y.name}{y.is_current?" (current)":""}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={filterClass || "__all"} onValueChange={v => setFilterClass(v === "__all" ? "" : v)}>
            <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="ta-class-filter"><SelectValue placeholder="Filter by class" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all" data-testid="tac-all">All classes</SelectItem>
              {classes.map(c => <SelectItem key={c.id} value={c.id} data-testid={`tac-${c.id}`}>{c.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button disabled={!yearId || readonly} data-testid="btn-new-assignment" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> Assign</Button>
            </DialogTrigger>
            <DialogContent className="rounded-none max-w-md">
              <DialogHeader><DialogTitle>New teacher assignment</DialogTitle></DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label className="overline">Teacher</Label>
                  <Select value={form.teacher_user_id} onValueChange={v => setForm({ ...form, teacher_user_id: v })}>
                    <SelectTrigger className="rounded-none h-10 mt-2" data-testid="ta-teacher-select"><SelectValue placeholder="Choose teacher" /></SelectTrigger>
                    <SelectContent>{teachers.map(t => <SelectItem key={t.id} value={t.id} data-testid={`tat-${t.id}`}>{t.full_name || t.email}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="overline">Class</Label>
                  <Select value={form.class_id} onValueChange={v => setForm({ ...form, class_id: v, section_id: "" })}>
                    <SelectTrigger className="rounded-none h-10 mt-2" data-testid="ta-class-select"><SelectValue placeholder="Choose class" /></SelectTrigger>
                    <SelectContent>{classes.map(c => <SelectItem key={c.id} value={c.id} data-testid={`tacls-${c.id}`}>{c.name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="overline">Section</Label>
                  <Select value={form.section_id || "__none"} onValueChange={v => setForm({ ...form, section_id: v === "__none" ? "" : v })}>
                    <SelectTrigger className="rounded-none h-10 mt-2" data-testid="ta-section-select"><SelectValue placeholder="(any)" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none" data-testid="tas-none">(any section)</SelectItem>
                      {sectionsForForm.map(s => <SelectItem key={s.id} value={s.id} data-testid={`tas-${s.id}`}>Section {s.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="overline">Subject</Label>
                  <Select value={form.subject_id || "__none"} onValueChange={v => setForm({ ...form, subject_id: v === "__none" ? "" : v })}>
                    <SelectTrigger className="rounded-none h-10 mt-2" data-testid="ta-subject-select"><SelectValue placeholder="(class-teacher role)" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none" data-testid="tasub-none">(none — class role)</SelectItem>
                      {subjects.map(s => <SelectItem key={s.id} value={s.id} data-testid={`tasub-${s.id}`}>{s.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={form.is_class_teacher} onChange={e => setForm({ ...form, is_class_teacher: e.target.checked })} data-testid="ta-is-classteacher" />
                    Class teacher
                  </label>
                  <div><Label className="overline">Weekly periods</Label><Input type="number" value={form.weekly_periods} onChange={e => setForm({ ...form, weekly_periods: parseInt(e.target.value || "0") })} className={field} data-testid="ta-weekly" /></div>
                </div>
              </div>
              <DialogFooter><Button onClick={submit} data-testid="ta-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="mt-8 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="assignments-table">
          <TableHeader>
            <TableRow>
              <TableHead>Teacher</TableHead>
              <TableHead>Class</TableHead>
              <TableHead>Section</TableHead>
              <TableHead>Subject</TableHead>
              <TableHead>Weekly</TableHead>
              <TableHead className="text-right"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {assignments.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="ta-empty">No assignments in this year.</TableCell></TableRow>}
            {assignments.map(a => (
              <TableRow key={a.id} data-testid={`assignment-row-${a.id}`}>
                <TableCell className="font-heading font-semibold"><ChalkboardTeacher size={14} weight="duotone" className="text-[var(--klein)] inline mr-2"/>{teacherName(a.teacher_user_id)}</TableCell>
                <TableCell>{className(a.class_id)}</TableCell>
                <TableCell>{a.section_id ? sectionName(a.section_id) : "—"}</TableCell>
                <TableCell>
                  {a.is_class_teacher && <Star size={12} weight="fill" className="inline mr-1 text-[var(--accent-yellow)]"/>}
                  {subjectName(a.subject_id)}
                </TableCell>
                <TableCell className="font-mono text-xs">{a.weekly_periods ?? "—"}</TableCell>
                <TableCell className="text-right"><button onClick={() => del(a.id)} disabled={readonly} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)] disabled:opacity-30" data-testid={`btn-del-assign-${a.id}`}><Trash size={14}/></button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
