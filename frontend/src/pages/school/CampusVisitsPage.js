import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Link } from "react-router-dom";

const STATUSES = ["scheduled", "confirmed", "completed", "no_show", "cancelled"];

export default function CampusVisitsPage() {
  const [rows, setRows] = useState([]);
  const load = useCallback(async () => {
    try { const { data } = await api.get("/school/crm/visits"); setRows(data); }
    catch (e) { toast.error(formatApiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const setStatus = async (id, status) => {
    try { await api.patch(`/school/crm/visits/${id}`, { status }); toast.success(`Visit ${status.replace("_", " ")}`); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  return (
    <div data-testid="visits-page">
      <div className="overline mb-2">Front Porch · Campus Visits</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="visits-title">Campus visits</h1>
      <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Schedule visits from an inquiry. Outcomes are logged to the inquiry timeline.</div>
      <div className="mt-8 bg-white border border-[var(--tinted-grey-200)] overflow-x-auto">
        <Table data-testid="visits-table">
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead><TableHead>Time</TableHead><TableHead>Prospect</TableHead>
              <TableHead>Purpose</TableHead><TableHead>Visitors</TableHead><TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]">No campus visits scheduled.</TableCell></TableRow>}
            {rows.map(v => (
              <TableRow key={v.id} data-testid={`visit-row-${v.id}`}>
                <TableCell className="font-mono text-xs tabular">{v.scheduled_date}</TableCell>
                <TableCell className="font-mono text-xs">{v.start_time} → {v.end_time}</TableCell>
                <TableCell><Link className="klein-underline text-[var(--klein)] text-sm" to={`/school/admissions/inquiries/${v.lead_id}`}>{v.lead_name || "Open"}</Link> <span className="font-mono text-[10px] text-[var(--tinted-grey-500)]">{v.inquiry_number}</span></TableCell>
                <TableCell className="text-sm">{v.purpose || "—"}</TableCell>
                <TableCell className="tabular">{v.expected_visitors}</TableCell>
                <TableCell>
                  <Select value={v.status} onValueChange={(s) => setStatus(v.id, s)}>
                    <SelectTrigger className="h-8 w-[140px] rounded-none text-xs" data-testid={`visit-status-${v.id}`}><SelectValue /></SelectTrigger>
                    <SelectContent>{STATUSES.map(s => <SelectItem key={s} value={s} data-testid={`visit-status-opt-${s}`}>{s.replace("_", " ")}</SelectItem>)}</SelectContent>
                  </Select>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
