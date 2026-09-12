import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Plus, Trash, Buildings, IdentificationBadge } from "@phosphor-icons/react";
import { useStaffMeta } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";
const tabTrig = "rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold";

export default function DepartmentsDesignationsPage() {
  const { departments, designations, reload } = useStaffMeta();
  const [deptOpen, setDeptOpen] = useState(false);
  const [desigOpen, setDesigOpen] = useState(false);
  const [deptForm, setDeptForm] = useState({ name: "", code: "" });
  const [desigForm, setDesigForm] = useState({ title: "", code: "", is_teaching: false, department_id: "" });

  const createDept = async () => {
    if (!deptForm.name || !deptForm.code) return toast.error("Name & code required");
    try { await api.post("/school/staff/departments", deptForm); toast.success("Created"); setDeptOpen(false); setDeptForm({ name: "", code: "" }); reload(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const delDept = async (id) => {
    if (!window.confirm("Delete this department?")) return;
    try { await api.delete(`/school/staff/departments/${id}`); toast.success("Deleted"); reload(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const createDesig = async () => {
    if (!desigForm.title || !desigForm.code) return toast.error("Title & code required");
    try {
      const payload = { ...desigForm };
      if (!payload.department_id) delete payload.department_id;
      await api.post("/school/staff/designations", payload);
      toast.success("Created"); setDesigOpen(false);
      setDesigForm({ title: "", code: "", is_teaching: false, department_id: "" }); reload();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const delDesig = async (id) => {
    if (!window.confirm("Delete this designation?")) return;
    try { await api.delete(`/school/staff/designations/${id}`); toast.success("Deleted"); reload(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="dept-desig-page">
      <div className="overline mb-2">Staff Master</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="dd-title">Departments & designations</h1>
      <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Foundation for org structure</div>

      <Tabs defaultValue="depts" className="mt-6">
        <TabsList className="rounded-none bg-transparent h-auto border-b border-[var(--tinted-grey-200)] w-full justify-start p-0">
          <TabsTrigger value="depts" className={tabTrig} data-testid="tab-depts">Departments ({departments.length})</TabsTrigger>
          <TabsTrigger value="desigs" className={tabTrig} data-testid="tab-desigs">Designations ({designations.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="depts" className="mt-6">
          <div className="flex justify-end mb-4">
            <Dialog open={deptOpen} onOpenChange={setDeptOpen}>
              <DialogTrigger asChild><Button data-testid="btn-new-dept" className="rounded-full bg-[var(--klein)] text-white"><Plus size={14} className="mr-1"/> New department</Button></DialogTrigger>
              <DialogContent className="rounded-none max-w-md">
                <DialogHeader><DialogTitle>New department</DialogTitle></DialogHeader>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2"><Label className="overline">Name</Label><Input value={deptForm.name} onChange={e => setDeptForm({ ...deptForm, name: e.target.value })} className={field} data-testid="dept-name" /></div>
                  <div><Label className="overline">Code</Label><Input value={deptForm.code} onChange={e => setDeptForm({ ...deptForm, code: e.target.value })} className={field} data-testid="dept-code" /></div>
                </div>
                <DialogFooter><Button onClick={createDept} data-testid="dept-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          <div className="bg-white border border-[var(--tinted-grey-200)]">
            <Table data-testid="depts-table">
              <TableHeader><TableRow><TableHead>Code</TableHead><TableHead>Name</TableHead><TableHead>Description</TableHead><TableHead className="text-right"></TableHead></TableRow></TableHeader>
              <TableBody>
                {departments.length === 0 && <TableRow><TableCell colSpan={4} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="dept-empty">No departments.</TableCell></TableRow>}
                {departments.map(d => (
                  <TableRow key={d.id} data-testid={`dept-row-${d.id}`}>
                    <TableCell className="font-mono text-xs">{d.code}</TableCell>
                    <TableCell className="font-heading font-semibold"><Buildings size={14} weight="duotone" className="text-[var(--klein)] inline mr-2"/>{d.name}</TableCell>
                    <TableCell className="text-xs">{d.description || "—"}</TableCell>
                    <TableCell className="text-right"><button onClick={() => delDept(d.id)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)]" data-testid={`dept-del-${d.id}`}><Trash size={14}/></button></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="desigs" className="mt-6">
          <div className="flex justify-end mb-4">
            <Dialog open={desigOpen} onOpenChange={setDesigOpen}>
              <DialogTrigger asChild><Button data-testid="btn-new-desig" className="rounded-full bg-[var(--klein)] text-white"><Plus size={14} className="mr-1"/> New designation</Button></DialogTrigger>
              <DialogContent className="rounded-none max-w-md">
                <DialogHeader><DialogTitle>New designation</DialogTitle></DialogHeader>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2"><Label className="overline">Title</Label><Input value={desigForm.title} onChange={e => setDesigForm({ ...desigForm, title: e.target.value })} className={field} data-testid="desig-title" /></div>
                  <div><Label className="overline">Code</Label><Input value={desigForm.code} onChange={e => setDesigForm({ ...desigForm, code: e.target.value })} className={field} data-testid="desig-code" /></div>
                  <div><Label className="overline">Department</Label>
                    <Select value={desigForm.department_id || "__none"} onValueChange={v => setDesigForm({ ...desigForm, department_id: v === "__none" ? "" : v })}>
                      <SelectTrigger className="rounded-none h-10 mt-2" data-testid="desig-dept"><SelectValue placeholder="(none)"/></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none">None</SelectItem>
                        {departments.map(d => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <label className="col-span-2 flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={desigForm.is_teaching} onChange={e => setDesigForm({ ...desigForm, is_teaching: e.target.checked })} data-testid="desig-teaching" /> Teaching role
                  </label>
                </div>
                <DialogFooter><Button onClick={createDesig} data-testid="desig-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          <div className="bg-white border border-[var(--tinted-grey-200)]">
            <Table data-testid="desigs-table">
              <TableHeader><TableRow><TableHead>Code</TableHead><TableHead>Title</TableHead><TableHead>Dept</TableHead><TableHead>Teaching?</TableHead><TableHead className="text-right"></TableHead></TableRow></TableHeader>
              <TableBody>
                {designations.length === 0 && <TableRow><TableCell colSpan={5} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="desig-empty">No designations.</TableCell></TableRow>}
                {designations.map(d => {
                  const dept = departments.find(x => x.id === d.department_id);
                  return (
                    <TableRow key={d.id} data-testid={`desig-row-${d.id}`}>
                      <TableCell className="font-mono text-xs">{d.code}</TableCell>
                      <TableCell className="font-heading font-semibold"><IdentificationBadge size={14} weight="duotone" className="text-[var(--klein)] inline mr-2"/>{d.title}</TableCell>
                      <TableCell>{dept?.name || "—"}</TableCell>
                      <TableCell>{d.is_teaching ? "Yes" : "No"}</TableCell>
                      <TableCell className="text-right"><button onClick={() => delDesig(d.id)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)]" data-testid={`desig-del-${d.id}`}><Trash size={14}/></button></TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
