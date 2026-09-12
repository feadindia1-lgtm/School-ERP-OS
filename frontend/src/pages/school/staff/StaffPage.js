import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, MagnifyingGlass, IdentificationBadge, Users, ChalkboardTeacher, AirplaneTilt, CaretLeft, CaretRight } from "@phosphor-icons/react";
import { useStaffMeta, EMPLOYMENT_TYPES, EMPLOYMENT_STATUSES, STATUS_TONE } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";
const PAGE_SIZE = 25;

const KPI_META = [
  { key: "total", label: "Total staff", icon: IdentificationBadge, tone: "ink", testid: "kpi-total" },
  { key: "active", label: "Active", icon: Users, tone: "klein", testid: "kpi-active" },
  { key: "teaching", label: "Teaching", icon: ChalkboardTeacher, tone: "accent", testid: "kpi-teaching" },
  { key: "pending_leave_applications", label: "Pending leave", icon: AirplaneTilt, tone: "red", testid: "kpi-pending" },
];
const toneClass = {
  ink: "bg-[var(--ink)] text-white", klein: "bg-[var(--klein)] text-white",
  accent: "bg-[var(--accent-yellow)] text-[var(--ink)]", red: "bg-[var(--accent-red)] text-white",
};

export default function StaffPage() {
  const meta = useStaffMeta();
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState({});
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [deptId, setDeptId] = useState("");
  const [teach, setTeach] = useState("");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ first_name: "", last_name: "", employment_type: "full_time", joining_date: "", mobile_primary: "", department_id: "", designation_id: "", is_teaching_staff: false, employee_code: "" });

  const load = useCallback(async () => {
    try {
      const p = new URLSearchParams();
      if (q) p.set("q", q);
      if (status) p.set("status", status);
      if (deptId) p.set("department_id", deptId);
      if (teach) p.set("is_teaching_staff", teach);
      p.set("page", String(page)); p.set("page_size", String(PAGE_SIZE));
      const { data } = await api.get(`/school/staff/employees?${p}`);
      setRows(data.items); setTotal(data.total);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [q, status, deptId, teach, page]);
  const loadStats = useCallback(async () => {
    try { const { data } = await api.get("/school/staff/overview"); setStats(data); } catch { /* best-effort */ }
  }, []);
  useEffect(() => { load(); loadStats(); }, [load, loadStats]);

  const submit = async () => {
    if (!form.first_name) return toast.error("First name required");
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== "" && v !== null));
      await api.post("/school/staff/employees", payload);
      toast.success("Employee created"); setOpen(false);
      setForm({ first_name: "", last_name: "", employment_type: "full_time", joining_date: "", mobile_primary: "", department_id: "", designation_id: "", is_teaching_staff: false, employee_code: "" });
      load(); loadStats();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div data-testid="staff-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Staff Master</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="staff-title">Staff</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{total} matching · single authoritative registry</div>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="btn-new-employee" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> New employee</Button>
          </DialogTrigger>
          <DialogContent className="rounded-none max-w-lg">
            <DialogHeader><DialogTitle>New employee</DialogTitle></DialogHeader>
            <div className="grid grid-cols-2 gap-4">
              <div><Label className="overline">First name</Label><Input value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} className={field} data-testid="ne-first" /></div>
              <div><Label className="overline">Last name</Label><Input value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} className={field} data-testid="ne-last" /></div>
              <div><Label className="overline">Employee code (blank = auto)</Label><Input value={form.employee_code} onChange={e => setForm({ ...form, employee_code: e.target.value })} placeholder="Auto EMP-YYYY-NNNN" className={field} data-testid="ne-code" /></div>
              <div><Label className="overline">Mobile</Label><Input value={form.mobile_primary} onChange={e => setForm({ ...form, mobile_primary: e.target.value })} className={field} data-testid="ne-mobile" /></div>
              <div><Label className="overline">Department</Label>
                <Select value={form.department_id || "__none"} onValueChange={v => setForm({ ...form, department_id: v === "__none" ? "" : v })}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="ne-dept-select"><SelectValue placeholder="(none)" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none">None</SelectItem>
                    {meta.departments.map(d => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div><Label className="overline">Designation</Label>
                <Select value={form.designation_id || "__none"} onValueChange={v => setForm({ ...form, designation_id: v === "__none" ? "" : v })}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="ne-desig-select"><SelectValue placeholder="(none)" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none">None</SelectItem>
                    {meta.designations.map(d => <SelectItem key={d.id} value={d.id}>{d.title}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div><Label className="overline">Employment type</Label>
                <Select value={form.employment_type} onValueChange={v => setForm({ ...form, employment_type: v })}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="ne-type"><SelectValue /></SelectTrigger>
                  <SelectContent>{EMPLOYMENT_TYPES.map(t => <SelectItem key={t} value={t}>{t.replace("_", " ")}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="overline">Joining date</Label><Input type="date" value={form.joining_date} onChange={e => setForm({ ...form, joining_date: e.target.value })} className={field} data-testid="ne-joining" /></div>
              <label className="col-span-2 flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_teaching_staff} onChange={e => setForm({ ...form, is_teaching_staff: e.target.checked })} data-testid="ne-teaching" /> Teaching staff
              </label>
            </div>
            <DialogFooter><Button onClick={submit} data-testid="ne-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* KPIs */}
      <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
        {KPI_META.map(k => {
          const Icon = k.icon;
          return (
            <div key={k.key} className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid={k.testid}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="overline text-[10px]">{k.label}</div>
                  <div className="mt-2 font-heading font-black text-4xl tracking-tighter tabular-nums" data-testid={`${k.testid}-value`}>{stats[k.key] ?? 0}</div>
                </div>
                <div className={`h-9 w-9 flex items-center justify-center rounded-[3px] ${toneClass[k.tone]}`}><Icon size={18} weight="duotone" /></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Filters */}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[280px] flex-1 max-w-md">
          <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tinted-grey-400)]" />
          <Input value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => { if (e.key === "Enter") { setPage(1); load(); } }} placeholder="Search name, code, email" className="pl-9 h-11 rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)]" data-testid="staff-search" />
        </div>
        <Select value={status || "__all"} onValueChange={v => { setStatus(v === "__all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[160px] rounded-none h-11" data-testid="filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all">All statuses</SelectItem>
            {EMPLOYMENT_STATUSES.map(s => <SelectItem key={s} value={s}>{s.replace("_", " ")}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={deptId || "__all"} onValueChange={v => { setDeptId(v === "__all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[180px] rounded-none h-11" data-testid="filter-dept"><SelectValue placeholder="Department" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all">All departments</SelectItem>
            {meta.departments.map(d => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={teach || "__any"} onValueChange={v => { setTeach(v === "__any" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[160px] rounded-none h-11" data-testid="filter-teach"><SelectValue placeholder="Type" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__any">Any</SelectItem>
            <SelectItem value="true">Teaching</SelectItem>
            <SelectItem value="false">Non-teaching</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="mt-6 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="staff-table">
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Designation</TableHead>
              <TableHead>Dept</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Joined</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={7} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="staff-empty">No employees match.</TableCell></TableRow>}
            {rows.map(e => {
              const dept = meta.departments.find(d => d.id === e.department_id);
              const desig = meta.designations.find(d => d.id === e.designation_id);
              return (
                <TableRow key={e.id} data-testid={`emp-row-${e.employee_code}`} className="hover:bg-[var(--tinted-grey-100)] transition-colors">
                  <TableCell><Link className="klein-underline text-[var(--klein)] font-mono text-xs" to={`/school/staff/${e.id}`}>{e.employee_code}</Link></TableCell>
                  <TableCell className="font-heading font-semibold"><Link to={`/school/staff/${e.id}`}>{e.first_name} {e.last_name || ""}</Link></TableCell>
                  <TableCell>{desig?.title || "—"}</TableCell>
                  <TableCell>{dept?.name || "—"}</TableCell>
                  <TableCell className="capitalize">{(e.employment_type || "").replace("_", " ")}</TableCell>
                  <TableCell><span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${STATUS_TONE[e.status] || ""}`}>{(e.status || "").replace("_", " ")}</span></TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">{e.joining_date?.slice(0, 10) || "—"}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <div className="text-[var(--tinted-grey-500)]" data-testid="staff-page-info">Page {page} of {totalPages} · {total} total</div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} data-testid="staff-prev" className="rounded-none"><CaretLeft size={14}/> Prev</Button>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} data-testid="staff-next" className="rounded-none">Next <CaretRight size={14}/></Button>
          </div>
        </div>
      )}
    </div>
  );
}
