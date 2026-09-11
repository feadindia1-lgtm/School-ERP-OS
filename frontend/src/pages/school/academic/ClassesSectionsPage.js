import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, GraduationCap, UsersThree, Trash } from "@phosphor-icons/react";
import { useAcademicYears, useCurrentYear } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function ClassesSectionsPage() {
  const { years } = useAcademicYears();
  const { yearId, setYearId, currentYear } = useCurrentYear(years);
  const [classes, setClasses] = useState([]);
  const [sectionsByClass, setSectionsByClass] = useState({});
  const [teachers, setTeachers] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [classOpen, setClassOpen] = useState(false);
  const [classForm, setClassForm] = useState({ name: "", code: "", stream: "", order: 0 });
  const [sectionOpen, setSectionOpen] = useState(false);
  const [sectionForm, setSectionForm] = useState({ class_id: "", name: "", capacity: 30, class_teacher_user_id: "", room_id: "" });

  const readonly = currentYear?.status === "archived";

  const load = useCallback(async () => {
    if (!yearId) return;
    try {
      const [cs, ts, rs] = await Promise.all([
        api.get(`/school/academic/classes?academic_year_id=${yearId}`),
        api.get(`/school/users?role=teacher`).catch(() => ({ data: [] })),
        api.get(`/school/academic/rooms`),
      ]);
      setClasses(cs.data); setTeachers(ts.data.items || ts.data || []); setRooms(rs.data);
      const sectionMap = {};
      for (const c of cs.data) {
        const r = await api.get(`/school/academic/sections?class_id=${c.id}`);
        sectionMap[c.id] = r.data;
      }
      setSectionsByClass(sectionMap);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [yearId]);

  useEffect(() => { load(); }, [load]);

  const createClass = async () => {
    if (!classForm.name || !classForm.code) return toast.error("Name & code required");
    try {
      await api.post("/school/academic/classes", { ...classForm, academic_year_id: yearId });
      toast.success("Class created"); setClassOpen(false);
      setClassForm({ name: "", code: "", stream: "", order: 0 }); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const createSection = async () => {
    if (!sectionForm.class_id || !sectionForm.name) return toast.error("Class & name required");
    try {
      const payload = { ...sectionForm, academic_year_id: yearId };
      if (!payload.class_teacher_user_id) delete payload.class_teacher_user_id;
      if (!payload.room_id) delete payload.room_id;
      await api.post("/school/academic/sections", payload);
      toast.success("Section created"); setSectionOpen(false);
      setSectionForm({ class_id: "", name: "", capacity: 30, class_teacher_user_id: "", room_id: "" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const deleteClass = async (id) => {
    if (!window.confirm("Delete this class?")) return;
    try { await api.delete(`/school/academic/classes/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const deleteSection = async (id) => {
    if (!window.confirm("Delete this section?")) return;
    try { await api.delete(`/school/academic/sections/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="classes-sections-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Academic Framework</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="cs-title">Classes & sections</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{classes.length} classes · {Object.values(sectionsByClass).flat().length} sections</div>
        </div>
        <div className="flex items-center gap-3">
          <Select value={yearId} onValueChange={setYearId}>
            <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="cs-year-select"><SelectValue placeholder="Select year" /></SelectTrigger>
            <SelectContent>{years.map(y => <SelectItem key={y.id} value={y.id} data-testid={`csy-${y.id}`}>{y.name}{y.is_current?" (current)":""}</SelectItem>)}</SelectContent>
          </Select>
          <Dialog open={classOpen} onOpenChange={setClassOpen}>
            <DialogTrigger asChild>
              <Button disabled={!yearId || readonly} data-testid="btn-new-class" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> Class</Button>
            </DialogTrigger>
            <DialogContent className="rounded-none max-w-md">
              <DialogHeader><DialogTitle>New class</DialogTitle></DialogHeader>
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2"><Label className="overline">Name</Label><Input placeholder="Grade 5" value={classForm.name} onChange={e => setClassForm({ ...classForm, name: e.target.value })} className={field} data-testid="cl-name" /></div>
                <div><Label className="overline">Code</Label><Input placeholder="5" value={classForm.code} onChange={e => setClassForm({ ...classForm, code: e.target.value })} className={field} data-testid="cl-code" /></div>
                <div><Label className="overline">Order</Label><Input type="number" value={classForm.order} onChange={e => setClassForm({ ...classForm, order: parseInt(e.target.value || "0") })} className={field} data-testid="cl-order" /></div>
                <div className="col-span-2"><Label className="overline">Stream (optional)</Label><Input placeholder="Science" value={classForm.stream} onChange={e => setClassForm({ ...classForm, stream: e.target.value })} className={field} data-testid="cl-stream" /></div>
              </div>
              <DialogFooter><Button onClick={createClass} data-testid="cl-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {readonly && <div className="mt-4 text-xs px-3 py-2 bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)] uppercase tracking-widest" data-testid="cs-readonly">This year is archived — read only.</div>}

      <div className="mt-8 space-y-6">
        {classes.length === 0 && (
          <div className="text-sm text-[var(--tinted-grey-500)] bg-white border border-[var(--tinted-grey-200)] p-6" data-testid="cs-empty">
            No classes yet. Create your first class to add sections underneath.
          </div>
        )}
        {classes.map(c => (
          <div key={c.id} className="bg-white border border-[var(--tinted-grey-200)]" data-testid={`class-block-${c.id}`}>
            <div className="flex items-center justify-between p-4 border-b border-[var(--tinted-grey-200)]">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 bg-[var(--klein)] text-white flex items-center justify-center">
                  <GraduationCap size={18} weight="duotone" />
                </div>
                <div>
                  <div className="font-heading font-bold">{c.name}</div>
                  <div className="text-xs text-[var(--tinted-grey-500)]"><span className="font-mono">{c.code}</span>{c.stream ? ` · ${c.stream}` : ""}{typeof c.order === "number" ? ` · order ${c.order}` : ""}</div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={readonly} onClick={() => { setSectionForm({ ...sectionForm, class_id: c.id }); setSectionOpen(true); }} data-testid={`btn-add-section-${c.id}`} className="rounded-none"><Plus size={12} className="mr-1"/> Section</Button>
                <Button size="sm" variant="outline" disabled={readonly} onClick={() => deleteClass(c.id)} data-testid={`btn-del-class-${c.id}`} className="rounded-none text-[var(--accent-red)]"><Trash size={12}/></Button>
              </div>
            </div>
            <div className="divide-y divide-[var(--tinted-grey-200)]">
              {(sectionsByClass[c.id] || []).length === 0 && <div className="p-4 text-xs text-[var(--tinted-grey-500)]" data-testid={`sec-empty-${c.id}`}>No sections in this class yet.</div>}
              {(sectionsByClass[c.id] || []).map(s => {
                const teacher = teachers.find(t => t.id === s.class_teacher_user_id);
                const room = rooms.find(r => r.id === s.room_id);
                return (
                  <div key={s.id} className="p-3 flex items-center justify-between" data-testid={`section-row-${s.id}`}>
                    <div className="flex items-center gap-3">
                      <UsersThree size={16} weight="duotone" className="text-[var(--klein)]" />
                      <div>
                        <div className="text-sm font-semibold">Section {s.name}</div>
                        <div className="text-xs text-[var(--tinted-grey-500)]">
                          {s.capacity ? `cap ${s.capacity}` : "no cap"}
                          {teacher ? ` · ${teacher.full_name || teacher.email}` : ""}
                          {room ? ` · ${room.code}` : ""}
                        </div>
                      </div>
                    </div>
                    <button disabled={readonly} onClick={() => deleteSection(s.id)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)] disabled:opacity-30" data-testid={`btn-del-section-${s.id}`}><Trash size={14} /></button>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <Dialog open={sectionOpen} onOpenChange={setSectionOpen}>
        <DialogContent className="rounded-none max-w-md">
          <DialogHeader><DialogTitle>New section</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div>
              <Label className="overline">Class</Label>
              <Select value={sectionForm.class_id} onValueChange={v => setSectionForm({ ...sectionForm, class_id: v })}>
                <SelectTrigger className="rounded-none h-10 mt-2" data-testid="sec-class-select"><SelectValue placeholder="Choose class" /></SelectTrigger>
                <SelectContent>{classes.map(c => <SelectItem key={c.id} value={c.id} data-testid={`scl-${c.id}`}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div><Label className="overline">Name</Label><Input placeholder="A" value={sectionForm.name} onChange={e => setSectionForm({ ...sectionForm, name: e.target.value })} className={field} data-testid="sec-name" /></div>
              <div><Label className="overline">Capacity</Label><Input type="number" value={sectionForm.capacity} onChange={e => setSectionForm({ ...sectionForm, capacity: parseInt(e.target.value || "0") })} className={field} data-testid="sec-cap" /></div>
            </div>
            <div>
              <Label className="overline">Class teacher</Label>
              <Select value={sectionForm.class_teacher_user_id || "__none"} onValueChange={v => setSectionForm({ ...sectionForm, class_teacher_user_id: v === "__none" ? "" : v })}>
                <SelectTrigger className="rounded-none h-10 mt-2" data-testid="sec-teacher-select"><SelectValue placeholder="Optional" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none" data-testid="st-none">None</SelectItem>
                  {teachers.filter(t => ["teacher","class_teacher"].includes(t.role)).map(t => <SelectItem key={t.id} value={t.id} data-testid={`st-${t.id}`}>{t.full_name || t.email}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="overline">Room</Label>
              <Select value={sectionForm.room_id || "__none"} onValueChange={v => setSectionForm({ ...sectionForm, room_id: v === "__none" ? "" : v })}>
                <SelectTrigger className="rounded-none h-10 mt-2" data-testid="sec-room-select"><SelectValue placeholder="Optional" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none" data-testid="sr-none">None</SelectItem>
                  {rooms.map(r => <SelectItem key={r.id} value={r.id} data-testid={`sr-${r.id}`}>{r.code} · {r.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter><Button onClick={createSection} data-testid="sec-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
