import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { LinkSimple, Warning } from "@phosphor-icons/react";

function LinkRow({ row, onLink }) {
  const best = row.suggestions[0];
  return (
    <div className="flex items-center justify-between gap-3 py-2 border-b border-[var(--tinted-grey-100)] last:border-0 text-sm" data-testid={`link-row-${row.employee_id}`}>
      <div>
        <Link to={`/school/staff/${row.employee_id}`} className="font-heading font-semibold">{row.name}</Link>
        <span className="font-mono text-xs text-[var(--tinted-grey-500)] ml-2">{row.employee_code}</span>
        {row.is_teaching_staff && <span className="ml-2 text-[10px] uppercase tracking-widest text-[var(--klein)]">teaching</span>}
      </div>
      {best ? (
        <Button size="sm" variant="outline" className="rounded-none" onClick={() => onLink(row.employee_id, best.id)} data-testid={`btn-link-suggest-${row.employee_id}`}>
          <LinkSimple size={14} className="mr-1" />Link to {best.email}
        </Button>
      ) : (
        <Link to={`/school/staff/${row.employee_id}`} className="text-xs underline" data-testid={`link-open-${row.employee_id}`}>Create login →</Link>
      )}
    </div>
  );
}

export function AccountLinksBanner({ onChanged }) {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const load = async () => {
    try { const { data: d } = await api.get("/school/staff/account-links"); setData(d); } catch { setData(null); }
  };
  useEffect(() => { load(); }, []);
  if (!data || data.unlinked_employees.length === 0) return null;
  const link = async (eid, uid) => {
    try {
      await api.post(`/school/staff/employees/${eid}/account/link`, { user_id: uid });
      toast.success("Linked"); load(); onChanged?.();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  return (
    <div className="mt-6 border border-amber-300 bg-amber-50 p-4 flex items-center justify-between flex-wrap gap-3" data-testid="account-links-banner">
      <div className="text-sm flex items-center gap-2">
        <Warning size={16} className="text-amber-700" />
        <span><b data-testid="unlinked-count">{data.unlinked_employees.length}</b> employee(s) have no login account. Unlinked teachers can't be assigned to classes or the timetable.</span>
      </div>
      <Button size="sm" className="rounded-full bg-[var(--ink)] text-white" onClick={() => setOpen(true)} data-testid="btn-review-links">Review & link</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="rounded-none max-w-2xl max-h-[80vh] overflow-y-auto" data-testid="account-links-dialog">
          <DialogHeader><DialogTitle>Link staff to existing logins</DialogTitle></DialogHeader>
          <div className="text-xs text-[var(--tinted-grey-500)] mb-2">Suggestions match name or email. Linking never creates a duplicate record.</div>
          {data.unlinked_employees.map((r) => <LinkRow key={r.employee_id} row={r} onLink={link} />)}
        </DialogContent>
      </Dialog>
    </div>
  );
}
