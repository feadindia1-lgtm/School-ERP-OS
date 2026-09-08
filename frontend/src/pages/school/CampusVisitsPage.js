import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Link } from "react-router-dom";

export default function CampusVisitsPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/school/crm/visits");
        setRows(data);
      } catch (e) { toast.error(formatApiError(e)); }
    })();
  }, []);
  return (
    <div data-testid="visits-page">
      <div className="overline mb-2">Front Porch · Campus Visits</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="visits-title">Campus visits</h1>

      <div className="mt-8 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="visits-table">
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Time</TableHead>
              <TableHead>Prospect</TableHead>
              <TableHead>Purpose</TableHead>
              <TableHead>Visitors</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]">No campus visits scheduled.</TableCell></TableRow>}
            {rows.map(v => (
              <TableRow key={v.id}>
                <TableCell className="font-mono text-xs tabular">{v.scheduled_date}</TableCell>
                <TableCell className="font-mono text-xs">{v.start_time} → {v.end_time}</TableCell>
                <TableCell><Link className="klein-underline text-[var(--klein)] text-sm" to={`/school/admissions/inquiries/${v.lead_id}`}>Open</Link></TableCell>
                <TableCell className="text-sm">{v.purpose || "—"}</TableCell>
                <TableCell className="tabular">{v.expected_visitors}</TableCell>
                <TableCell><span className="text-xs uppercase tracking-widest">{v.status}</span></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
