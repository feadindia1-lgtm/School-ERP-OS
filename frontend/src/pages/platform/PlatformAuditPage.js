import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";

export default function PlatformAuditPage() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");

  const load = async (prefix = "") => {
    try {
      const params = new URLSearchParams({ limit: "200" });
      if (prefix) params.set("action_prefix", prefix);
      const { data } = await api.get(`/platform/audit-logs?${params.toString()}`);
      setRows(data);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); }, []);

  return (
    <div data-testid="audit-page">
      <div className="overline mb-3">Audit</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter">Platform audit trail</h1>

      <div className="mt-6 max-w-md">
        <Input
          data-testid="audit-filter"
          placeholder="Filter by action prefix (e.g. impersonation.)"
          value={q}
          onChange={(e)=>setQ(e.target.value)}
          onKeyDown={(e)=>{ if(e.key==="Enter") load(q); }}
          className="h-11 rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)]"
        />
      </div>

      <div className="mt-6 bg-white border border-[var(--tinted-grey-200)] overflow-x-auto">
        <Table data-testid="audit-table">
          <TableHeader>
            <TableRow>
              <TableHead>Timestamp</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead>Tenant</TableHead>
              <TableHead>IP</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]">No events.</TableCell></TableRow>}
            {rows.map(l => (
              <TableRow key={l.id}>
                <TableCell className="font-mono text-xs tabular whitespace-nowrap">{new Date(l.created_at).toISOString().replace("T"," ").slice(0,19)}</TableCell>
                <TableCell><code className="text-xs text-[var(--klein)]">{l.action}</code></TableCell>
                <TableCell className="text-xs">{l.actor_email || "—"}</TableCell>
                <TableCell className="text-xs">{l.resource}{l.resource_id ? ` · ${l.resource_id.slice(-6)}` : ""}</TableCell>
                <TableCell className="font-mono text-xs">{l.tenant_id ? l.tenant_id.slice(-6) : "platform"}</TableCell>
                <TableCell className="font-mono text-xs">{l.ip || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
