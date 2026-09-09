import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, MagnifyingGlass, GraduationCap, CheckCircle, Sparkle, WarningCircle, CaretLeft, CaretRight } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";
const STATES = ["ACTIVE", "INACTIVE", "ON_LEAVE", "TRANSFERRED", "WITHDRAWN", "GRADUATED", "ALUMNI", "PROSPECT"];
const PAGE_SIZE = 25;

const KPI_META = [
  { key: "total", label: "Total students", icon: GraduationCap, tone: "ink", testid: "kpi-total" },
  { key: "active", label: "Active", icon: CheckCircle, tone: "klein", testid: "kpi-active" },
  { key: "new_this_year", label: "New this year", icon: Sparkle, tone: "accent", testid: "kpi-new" },
  { key: "missing_info", label: "Missing info", icon: WarningCircle, tone: "red", testid: "kpi-missing" },
];

const toneClass = {
  ink: "bg-[var(--ink)] text-white",
  klein: "bg-[var(--klein)] text-white",
  accent: "bg-[var(--accent-yellow)] text-[var(--ink)]",
  red: "bg-[var(--accent-red)] text-white",
};

export default function StudentsPage() {
  const { tenant } = useAuth();
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState({ total: 0, active: 0, new_this_year: 0, missing_info: 0 });
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [academicYear, setAcademicYear] = useState("");
  const [className, setClassName] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("newest");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ first_name: "", last_name: "", date_of_birth: "", gender: "", class_name: "", section: "", academic_year: "" });

  const currentYear = useMemo(() => tenant?.academic?.current_year || "", [tenant]);
  useEffect(() => {
    if (currentYear && !academicYear) setAcademicYear(currentYear);
  }, [currentYear]); // eslint-disable-line

  const loadStats = useCallback(async () => {
    try {
      const p = new URLSearchParams();
      if (currentYear) p.set("academic_year", currentYear);
      const { data } = await api.get(`/school/students/stats?${p}`);
      setStats(data);
    } catch (e) { /* KPI is best-effort */ }
  }, [currentYear]);

  const load = useCallback(async () => {
    try {
      const p = new URLSearchParams();
      if (q) p.set("q", q);
      if (status) p.set("status", status);
      if (academicYear) p.set("academic_year", academicYear);
      if (className) p.set("class_name", className);
      p.set("page", String(page));
      p.set("page_size", String(PAGE_SIZE));
      const { data } = await api.get(`/school/students?${p}`);
      let items = data.items || [];
      if (sort === "name") items = [...items].sort((a, b) => (a.first_name || "").localeCompare(b.first_name || ""));
      if (sort === "admission") items = [...items].sort((a, b) => (b.admission_number || "").localeCompare(a.admission_number || ""));
      setRows(items);
      setTotal(data.total);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [q, status, academicYear, className, page, sort]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadStats(); }, [loadStats]);

  const submit = async () => {
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ""));
      await api.post("/school/students", payload);
      toast.success("Student created");
      setOpen(false);
      setForm({ first_name: "", last_name: "", date_of_birth: "", gender: "", class_name: "", section: "", academic_year: "" });
      load(); loadStats();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div data-testid="students-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Student Master</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="students-title">
            All students
          </h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">
            {total} matching · single authoritative registry
          </div>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="btn-new-student" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white">
              <Plus size={14} className="mr-1" /> New student
            </Button>
          </DialogTrigger>
          <DialogContent className="rounded-none max-w-lg">
            <DialogHeader><DialogTitle>New student</DialogTitle></DialogHeader>
            <div className="grid grid-cols-2 gap-4">
              <div><Label className="overline">First name</Label><Input value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} className={field} data-testid="st-first" /></div>
              <div><Label className="overline">Last name</Label><Input value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} className={field} data-testid="st-last" /></div>
              <div><Label className="overline">Date of birth</Label><Input type="date" value={form.date_of_birth} onChange={e => setForm({ ...form, date_of_birth: e.target.value })} className={field} data-testid="st-dob" /></div>
              <div><Label className="overline">Gender</Label><Input value={form.gender} onChange={e => setForm({ ...form, gender: e.target.value })} className={field} data-testid="st-gender" /></div>
              <div><Label className="overline">Class</Label><Input value={form.class_name} onChange={e => setForm({ ...form, class_name: e.target.value })} className={field} data-testid="st-class" /></div>
              <div><Label className="overline">Section</Label><Input value={form.section} onChange={e => setForm({ ...form, section: e.target.value })} className={field} data-testid="st-section" /></div>
              <div className="col-span-2"><Label className="overline">Academic year</Label><Input value={form.academic_year} onChange={e => setForm({ ...form, academic_year: e.target.value })} className={field} data-testid="st-ay" /></div>
            </div>
            <DialogFooter>
              <Button onClick={submit} data-testid="st-submit" className="rounded-none bg-[var(--klein)] hover:opacity-90 text-white">Create</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* KPI cards */}
      <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
        {KPI_META.map((k) => {
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
              {k.key === "missing_info" && (stats.missing_dob > 0 || stats.missing_guardians > 0) ? (
                <div className="mt-2 text-[10px] text-[var(--tinted-grey-500)] uppercase tracking-widest">
                  {stats.missing_dob || 0} no DOB · {stats.missing_guardians || 0} no guardian
                </div>
              ) : null}
              {k.key === "new_this_year" && currentYear ? (
                <div className="mt-2 text-[10px] text-[var(--tinted-grey-500)] uppercase tracking-widest">Year {currentYear}</div>
              ) : null}
            </div>
          );
        })}
      </div>

      {/* Filters */}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[280px] flex-1 max-w-md">
          <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tinted-grey-400)]" />
          <Input
            value={q}
            onChange={e => setQ(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") { setPage(1); load(); } }}
            placeholder="Search name, admission #, roll #"
            className="pl-9 h-11 rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)]"
            data-testid="students-search"
          />
        </div>
        <Select value={status || "__all"} onValueChange={(v) => { setStatus(v === "__all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[160px] rounded-none h-11" data-testid="filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all" data-testid="fst-all">All statuses</SelectItem>
            {STATES.map(s => <SelectItem key={s} value={s} data-testid={`fst-${s}`}>{s}</SelectItem>)}
          </SelectContent>
        </Select>
        <Input placeholder="Class" value={className} onChange={e => setClassName(e.target.value)} onKeyDown={e => { if (e.key === "Enter") { setPage(1); load(); } }} className="h-11 w-[120px] rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)]" data-testid="filter-class" />
        <Input placeholder="Year" value={academicYear} onChange={e => setAcademicYear(e.target.value)} onKeyDown={e => { if (e.key === "Enter") { setPage(1); load(); } }} className="h-11 w-[110px] rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)]" data-testid="filter-year" />
        <Select value={sort} onValueChange={setSort}>
          <SelectTrigger className="w-[150px] rounded-none h-11" data-testid="filter-sort"><SelectValue placeholder="Sort" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="newest" data-testid="sort-newest">Newest first</SelectItem>
            <SelectItem value="name" data-testid="sort-name">Name (A-Z)</SelectItem>
            <SelectItem value="admission" data-testid="sort-admission">Admission #</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="mt-6 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="students-table">
          <TableHeader>
            <TableRow>
              <TableHead>Admission #</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Class / Section</TableHead>
              <TableHead>Roll #</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="students-empty">No students match these filters.</TableCell>
              </TableRow>
            )}
            {rows.map(s => (
              <TableRow key={s.id} data-testid={`student-row-${s.admission_number}`} className="hover:bg-[var(--tinted-grey-100)] transition-colors">
                <TableCell>
                  <Link className="klein-underline text-[var(--klein)] font-mono text-xs" to={`/school/students/${s.id}`}>{s.admission_number}</Link>
                </TableCell>
                <TableCell className="font-heading font-semibold">
                  <Link to={`/school/students/${s.id}`}>{s.first_name} {s.last_name || ""}</Link>
                </TableCell>
                <TableCell>{s.class_name || "—"}{s.section ? ` · ${s.section}` : ""}</TableCell>
                <TableCell className="font-mono text-xs">{s.roll_number || "—"}</TableCell>
                <TableCell>
                  <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${s.status === "ACTIVE" ? "bg-[var(--klein)] text-white" : "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]"}`}>
                    {s.status}
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">{new Date(s.created_at).toISOString().slice(0, 10)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <div className="text-[var(--tinted-grey-500)]" data-testid="page-info">Page {page} of {totalPages} · {total} total</div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} data-testid="page-prev" className="rounded-none">
              <CaretLeft size={14} /> Prev
            </Button>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} data-testid="page-next" className="rounded-none">
              Next <CaretRight size={14} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
