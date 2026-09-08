import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MagnifyingGlass } from "@phosphor-icons/react";

const STATUSES = ["DRAFT","SUBMITTED","UNDER_REVIEW","DOCUMENTS_PENDING","APPROVED","REJECTED","WITHDRAWN","CONVERTED"];

export default function ApplicationsPage() {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");

  const load = async () => {
    try {
      const params = new URLSearchParams({ page: "1", page_size: "100" });
      if (q) params.set("q", q);
      if (status !== "all") params.set("status", status);
      const { data } = await api.get(`/school/admissions/applications?${params.toString()}`);
      setRows(data.items); setTotal(data.total);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  const color = (s) => s === "APPROVED" || s === "CONVERTED" ? "var(--klein)" : s === "REJECTED" || s === "WITHDRAWN" ? "var(--accent-red)" : "var(--accent-yellow)";

  return (
    <div data-testid="applications-page">
      <div className="overline mb-2">Front Porch · Applications</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="applications-title">Applications</h1>
      <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{total} applications</div>

      <div className="mt-6 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-[420px]">
          <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tinted-grey-400)]" />
          <Input
            value={q} onChange={(e)=>setQ(e.target.value)} onKeyDown={(e)=>{ if (e.key==="Enter") load(); }}
            placeholder="Search name, mobile, application #"
            className="pl-9 h-11 rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)]"
            data-testid="apps-search"
          />
        </div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="rounded-none h-11 w-[240px]" data-testid="apps-filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUSES.map(s => <SelectItem key={s} value={s} data-testid={`apps-status-${s}`}>{s.replace(/_/g," ")}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="mt-6 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="applications-table">
          <TableHeader>
            <TableRow>
              <TableHead>App #</TableHead>
              <TableHead>Student</TableHead>
              <TableHead>Class</TableHead>
              <TableHead>Parent</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]">No applications.</TableCell></TableRow>}
            {rows.map(a => (
              <TableRow key={a.id} data-testid={`app-row-${a.application_number}`}>
                <TableCell><Link className="klein-underline font-mono text-xs text-[var(--klein)]" to={`/school/admissions/applications/${a.id}`}>{a.application_number}</Link></TableCell>
                <TableCell className="font-heading font-semibold">{a.student_first_name} {a.student_last_name}</TableCell>
                <TableCell>{a.class_requested} · {a.academic_year}</TableCell>
                <TableCell className="text-sm">{a.parent_name}<div className="font-mono text-[10px] text-[var(--tinted-grey-500)]">{a.parent_mobile}</div></TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-1.5 text-xs">
                    <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color(a.status) }} />
                    <span className="uppercase tracking-widest text-[10px]">{a.status}</span>
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono text-xs tabular">{new Date(a.created_at).toISOString().slice(0,10)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
