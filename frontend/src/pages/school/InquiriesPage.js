import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Kanban, ListBullets, Plus, MagnifyingGlass } from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import CreateInquiryDialog from "./crm/CreateInquiryDialog";
import KanbanBoard from "./crm/KanbanBoard";

const PAGE_SIZE = 25;

export default function InquiriesPage() {
  const [sp, setSp] = useSearchParams();
  const view = sp.get("view") || "kanban";
  const [q, setQ] = useState("");
  const [stage, setStage] = useState("all");
  const [priority, setPriority] = useState("all");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [openCreate, setOpenCreate] = useState(false);
  const [settings, setSettings] = useState(null);

  const load = async () => {
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (q) params.set("q", q);
      if (stage !== "all") params.set("stage", stage);
      if (priority !== "all") params.set("priority", priority);
      const { data } = await api.get(`/school/crm/leads?${params.toString()}`);
      setItems(data.items); setTotal(data.total);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [page, stage, priority]);
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/school/crm/settings");
        setSettings(data);
      } catch {}
    })();
  }, []);

  const stages = settings?.pipeline_stages || [];
  const priorities = settings?.priorities || ["low","medium","high","urgent"];

  return (
    <div data-testid="inquiries-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Front Porch · Inquiries</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="inquiries-title">Prospect pipeline</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{total} inquiries</div>
        </div>
        <div className="flex items-center gap-3">
          <div className="inline-flex bg-white border border-[var(--tinted-grey-300)]">
            <button onClick={() => setSp({ view: "kanban" })} className={`px-3 py-2 text-xs uppercase tracking-widest flex items-center gap-1 ${view === "kanban" ? "bg-[var(--ink)] text-white" : ""}`} data-testid="view-kanban">
              <Kanban size={14} /> Kanban
            </button>
            <button onClick={() => setSp({ view: "list" })} className={`px-3 py-2 text-xs uppercase tracking-widest flex items-center gap-1 ${view === "list" ? "bg-[var(--ink)] text-white" : ""}`} data-testid="view-list">
              <ListBullets size={14} /> List
            </button>
          </div>
          <Button data-testid="btn-new-inquiry" onClick={() => setOpenCreate(true)} className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white transition-opacity">
            <Plus size={16} className="mr-1" /> New inquiry
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="mt-6 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-[420px]">
          <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tinted-grey-400)]" />
          <Input
            data-testid="inquiries-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { setPage(1); load(); } }}
            placeholder="Search name, mobile, email, inquiry #"
            className="pl-9 h-11 rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)]"
          />
        </div>
        <Select value={stage} onValueChange={(v) => { setStage(v); setPage(1); }}>
          <SelectTrigger className="rounded-none h-11 w-[220px]" data-testid="filter-stage"><SelectValue placeholder="All stages" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All stages</SelectItem>
            {stages.map(s => <SelectItem key={s.code} value={s.code} data-testid={`filter-stage-${s.code}`}>{s.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={priority} onValueChange={(v) => { setPriority(v); setPage(1); }}>
          <SelectTrigger className="rounded-none h-11 w-[180px]" data-testid="filter-priority"><SelectValue placeholder="Priority" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All priorities</SelectItem>
            {priorities.map(p => <SelectItem key={p} value={p} data-testid={`filter-priority-${p}`}>{p}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* View */}
      {view === "kanban" ? (
        <KanbanBoard leads={items} stages={stages} reload={load} />
      ) : (
        <div className="mt-6 bg-white border border-[var(--tinted-grey-200)]">
          <Table data-testid="inquiries-table">
            <TableHeader>
              <TableRow>
                <TableHead>Inquiry #</TableHead>
                <TableHead>Student</TableHead>
                <TableHead>Parent</TableHead>
                <TableHead>Class</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead className="text-right">Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 && <TableRow><TableCell colSpan={7} className="text-center py-10 text-[var(--tinted-grey-500)]">No inquiries.</TableCell></TableRow>}
              {items.map(l => (
                <TableRow key={l.id} data-testid={`lead-row-${l.inquiry_number}`}>
                  <TableCell><Link to={`/school/admissions/inquiries/${l.id}`} className="font-mono text-xs klein-underline text-[var(--klein)]">{l.inquiry_number}</Link></TableCell>
                  <TableCell className="font-heading font-semibold">{l.student_first_name} {l.student_last_name}</TableCell>
                  <TableCell className="text-sm">{l.parent_name}<div className="font-mono text-xs text-[var(--tinted-grey-500)]">{l.parent_mobile}</div></TableCell>
                  <TableCell>{l.class_seeking || "—"}</TableCell>
                  <TableCell><span className="text-xs uppercase tracking-widest">{l.stage}</span></TableCell>
                  <TableCell><span className="text-xs capitalize">{l.priority}</span></TableCell>
                  <TableCell className="text-right font-mono text-xs tabular">{new Date(l.created_at).toISOString().slice(0,10)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="p-3 flex items-center justify-between border-t border-[var(--tinted-grey-200)] text-sm">
            <span className="text-[var(--tinted-grey-500)]">Page {page} · {items.length}/{total}</span>
            <div className="flex gap-2">
              <Button size="sm" variant="ghost" disabled={page===1} onClick={()=>setPage(p=>Math.max(1,p-1))} data-testid="page-prev">Prev</Button>
              <Button size="sm" variant="ghost" disabled={page*PAGE_SIZE>=total} onClick={()=>setPage(p=>p+1)} data-testid="page-next">Next</Button>
            </div>
          </div>
        </div>
      )}

      <CreateInquiryDialog open={openCreate} onOpenChange={setOpenCreate} settings={settings} onCreated={load} />
    </div>
  );
}
