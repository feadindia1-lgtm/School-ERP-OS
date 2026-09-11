import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Plus, Trash, BookOpen, Stack } from "@phosphor-icons/react";
import { useAcademicYears, useCurrentYear, SUBJECT_TYPES } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";
const tabTrig = "rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold";

export default function SubjectsPage() {
  const { years } = useAcademicYears();
  const { yearId, setYearId, currentYear } = useCurrentYear(years);
  const readonly = currentYear?.status === "archived";
  const [subjects, setSubjects] = useState([]);
  const [groups, setGroups] = useState([]);
  const [classes, setClasses] = useState([]);
  const [subjOpen, setSubjOpen] = useState(false);
  const [grpOpen, setGrpOpen] = useState(false);
  const [subjForm, setSubjForm] = useState({ name: "", code: "", subject_type: "theory", is_optional: false });
  const [grpForm, setGrpForm] = useState({ class_id: "", name: "", subject_ids: [] });

  const load = useCallback(async () => {
    try {
      const [s, g, c] = await Promise.all([
        api.get(`/school/academic/subjects`),
        yearId ? api.get(`/school/academic/subject-groups?academic_year_id=${yearId}`) : Promise.resolve({ data: [] }),
        yearId ? api.get(`/school/academic/classes?academic_year_id=${yearId}`) : Promise.resolve({ data: [] }),
      ]);
      setSubjects(s.data); setGroups(g.data); setClasses(c.data);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [yearId]);
  useEffect(() => { load(); }, [load]);

  const createSubject = async () => {
    if (!subjForm.name || !subjForm.code) return toast.error("Name & code required");
    try { await api.post("/school/academic/subjects", subjForm); toast.success("Subject created"); setSubjOpen(false); setSubjForm({ name: "", code: "", subject_type: "theory", is_optional: false }); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const deleteSubject = async (id) => {
    if (!window.confirm("Delete this subject?")) return;
    try { await api.delete(`/school/academic/subjects/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const createGroup = async () => {
    if (!grpForm.class_id || !grpForm.name) return toast.error("Class & name required");
    try {
      await api.post("/school/academic/subject-groups", { ...grpForm, academic_year_id: yearId });
      toast.success("Subject group created"); setGrpOpen(false);
      setGrpForm({ class_id: "", name: "", subject_ids: [] }); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const deleteGroup = async (id) => {
    if (!window.confirm("Delete this group?")) return;
    try { await api.delete(`/school/academic/subject-groups/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const toggleGrpSubject = (sid) => {
    setGrpForm(f => ({ ...f, subject_ids: f.subject_ids.includes(sid) ? f.subject_ids.filter(x => x !== sid) : [...f.subject_ids, sid] }));
  };

  return (
    <div data-testid="subjects-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Academic Framework</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="subj-title">Subjects</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{subjects.length} subjects · {groups.length} groups</div>
        </div>
        <Select value={yearId} onValueChange={setYearId}>
          <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="subj-year-select"><SelectValue placeholder="Select year" /></SelectTrigger>
          <SelectContent>{years.map(y => <SelectItem key={y.id} value={y.id} data-testid={`sjy-${y.id}`}>{y.name}{y.is_current?" (current)":""}</SelectItem>)}</SelectContent>
        </Select>
      </div>

      <Tabs defaultValue="subjects" className="mt-6">
        <TabsList className="rounded-none bg-transparent h-auto border-b border-[var(--tinted-grey-200)] w-full justify-start p-0">
          <TabsTrigger value="subjects" className={tabTrig} data-testid="tab-subjects">Subjects ({subjects.length})</TabsTrigger>
          <TabsTrigger value="groups" className={tabTrig} data-testid="tab-groups">Subject groups ({groups.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="subjects" className="mt-6">
          <div className="flex justify-end mb-4">
            <Dialog open={subjOpen} onOpenChange={setSubjOpen}>
              <DialogTrigger asChild>
                <Button data-testid="btn-new-subject" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> New subject</Button>
              </DialogTrigger>
              <DialogContent className="rounded-none max-w-md">
                <DialogHeader><DialogTitle>New subject</DialogTitle></DialogHeader>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2"><Label className="overline">Name</Label><Input placeholder="Mathematics" value={subjForm.name} onChange={e => setSubjForm({ ...subjForm, name: e.target.value })} className={field} data-testid="sb-name" /></div>
                  <div><Label className="overline">Code</Label><Input placeholder="MATH" value={subjForm.code} onChange={e => setSubjForm({ ...subjForm, code: e.target.value })} className={field} data-testid="sb-code" /></div>
                  <div><Label className="overline">Type</Label>
                    <Select value={subjForm.subject_type} onValueChange={v => setSubjForm({ ...subjForm, subject_type: v })}>
                      <SelectTrigger className="rounded-none h-10 mt-2" data-testid="sb-type"><SelectValue /></SelectTrigger>
                      <SelectContent>{SUBJECT_TYPES.map(t => <SelectItem key={t} value={t} data-testid={`sbt-${t}`}>{t}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <label className="col-span-2 flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={subjForm.is_optional} onChange={e => setSubjForm({ ...subjForm, is_optional: e.target.checked })} data-testid="sb-optional" />
                    Optional subject
                  </label>
                </div>
                <DialogFooter><Button onClick={createSubject} data-testid="sb-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="bg-white border border-[var(--tinted-grey-200)]">
            <Table data-testid="subjects-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Code</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Optional</TableHead>
                  <TableHead className="text-right"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subjects.length === 0 && <TableRow><TableCell colSpan={5} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="subj-empty">No subjects yet.</TableCell></TableRow>}
                {subjects.map(s => (
                  <TableRow key={s.id} data-testid={`subject-row-${s.id}`}>
                    <TableCell className="font-heading font-semibold"><BookOpen size={14} weight="duotone" className="text-[var(--klein)] inline mr-2"/>{s.name}</TableCell>
                    <TableCell className="font-mono text-xs">{s.code}</TableCell>
                    <TableCell className="capitalize">{s.subject_type}</TableCell>
                    <TableCell>{s.is_optional ? "Yes" : "No"}</TableCell>
                    <TableCell className="text-right"><button onClick={() => deleteSubject(s.id)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)]" data-testid={`btn-del-subject-${s.id}`}><Trash size={14}/></button></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="groups" className="mt-6">
          <div className="flex justify-end mb-4">
            <Dialog open={grpOpen} onOpenChange={setGrpOpen}>
              <DialogTrigger asChild>
                <Button disabled={!yearId || readonly || subjects.length === 0 || classes.length === 0} data-testid="btn-new-group" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> New group</Button>
              </DialogTrigger>
              <DialogContent className="rounded-none max-w-lg">
                <DialogHeader><DialogTitle>New subject group</DialogTitle></DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label className="overline">Class</Label>
                    <Select value={grpForm.class_id} onValueChange={v => setGrpForm({ ...grpForm, class_id: v })}>
                      <SelectTrigger className="rounded-none h-10 mt-2" data-testid="grp-class-select"><SelectValue placeholder="Choose class" /></SelectTrigger>
                      <SelectContent>{classes.map(c => <SelectItem key={c.id} value={c.id} data-testid={`gcl-${c.id}`}>{c.name}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div><Label className="overline">Name</Label><Input placeholder="Grade 10 Core" value={grpForm.name} onChange={e => setGrpForm({ ...grpForm, name: e.target.value })} className={field} data-testid="grp-name" /></div>
                  <div>
                    <Label className="overline">Subjects</Label>
                    <div className="mt-2 max-h-[240px] overflow-y-auto border border-[var(--tinted-grey-200)] p-3 space-y-2">
                      {subjects.map(s => (
                        <label key={s.id} className="flex items-center gap-2 text-sm cursor-pointer">
                          <input type="checkbox" checked={grpForm.subject_ids.includes(s.id)} onChange={() => toggleGrpSubject(s.id)} data-testid={`gsub-${s.id}`} />
                          <span>{s.name} <span className="font-mono text-xs text-[var(--tinted-grey-500)]">{s.code}</span></span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
                <DialogFooter><Button onClick={createGroup} data-testid="grp-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="bg-white border border-[var(--tinted-grey-200)] divide-y divide-[var(--tinted-grey-200)]" data-testid="groups-list">
            {groups.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]" data-testid="grp-empty">No subject groups yet.</div>}
            {groups.map(g => {
              const cls = classes.find(c => c.id === g.class_id);
              return (
                <div key={g.id} className="p-4 flex items-start justify-between" data-testid={`group-row-${g.id}`}>
                  <div className="flex items-start gap-3">
                    <Stack size={18} weight="duotone" className="text-[var(--klein)] mt-1" />
                    <div>
                      <div className="font-heading font-semibold">{g.name}</div>
                      <div className="text-xs text-[var(--tinted-grey-500)]">{cls?.name || "—"} · {g.subject_ids?.length || 0} subject(s)</div>
                      <div className="text-xs text-[var(--tinted-grey-500)] mt-1">
                        {(g.subject_ids || []).map(id => subjects.find(s => s.id === id)?.code).filter(Boolean).join(" · ") || "—"}
                      </div>
                    </div>
                  </div>
                  <button onClick={() => deleteGroup(g.id)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)]" data-testid={`btn-del-group-${g.id}`}><Trash size={14}/></button>
                </div>
              );
            })}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
