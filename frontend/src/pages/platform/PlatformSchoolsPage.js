import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { MagnifyingGlass, Plus } from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function PlatformSchoolsPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (status !== "all") params.set("status", status);
      const { data } = await api.get(`/platform/tenants?${params.toString()}`);
      setRows(data);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  const filtered = useMemo(() => {
    if (!q) return rows;
    const s = q.toLowerCase();
    return rows.filter(r => r.name.toLowerCase().includes(s) || r.slug.includes(s) || (r.school_code || "").toLowerCase().includes(s));
  }, [rows, q]);

  return (
    <div data-testid="schools-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-3">Schools</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="schools-title">All tenants</h1>
        </div>
        <Link to="/platform/schools/new">
          <button data-testid="schools-cta-new" className="rounded-full bg-[var(--klein)] hover:bg-[var(--klein-hover)] text-white transition-colors h-11 px-6 inline-flex items-center gap-2">
            <Plus size={16} /> New school
          </button>
        </Link>
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-[420px]">
          <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tinted-grey-400)]" />
          <Input
            data-testid="schools-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") load(); }}
            placeholder="Search by name, slug or code…"
            className="pl-9 h-11 rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)]"
          />
        </div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="rounded-none h-11 w-[180px]" data-testid="schools-filter-status">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {["all", "active", "trial", "suspended", "archived"].map(s => (
              <SelectItem key={s} value={s} data-testid={`schools-filter-${s}`}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="mt-6 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="schools-table">
          <TableHeader>
            <TableRow>
              <TableHead>School</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Code</TableHead>
              <TableHead>Board</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && <TableRow><TableCell colSpan={7} className="text-center py-10 text-[var(--tinted-grey-500)]">Loading…</TableCell></TableRow>}
            {!loading && filtered.length === 0 && <TableRow><TableCell colSpan={7} className="text-center py-10 text-[var(--tinted-grey-500)]">No schools match.</TableCell></TableRow>}
            {filtered.map(t => (
              <TableRow key={t.id} data-testid={`school-row-${t.slug}`}>
                <TableCell>
                  <Link to={`/platform/schools/${t.id}`} className="font-heading font-semibold klein-underline">{t.name}</Link>
                  {t.short_name && <div className="text-xs text-[var(--tinted-grey-500)]">{t.short_name}</div>}
                </TableCell>
                <TableCell className="font-mono text-xs">{t.slug}</TableCell>
                <TableCell className="font-mono text-xs">{t.school_code || "—"}</TableCell>
                <TableCell className="text-xs uppercase tracking-widest">{t.board || "—"}</TableCell>
                <TableCell className="text-xs uppercase tracking-widest">{t.plan}</TableCell>
                <TableCell>
                  <span className={`inline-flex items-center gap-1.5 text-xs`}>
                    <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: t.status === "active" ? "var(--klein)" : t.status === "trial" ? "var(--accent-yellow)" : "var(--accent-red)" }} />
                    <span className="capitalize">{t.status}</span>
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono text-xs tabular">{new Date(t.created_at).toISOString().slice(0, 10)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
