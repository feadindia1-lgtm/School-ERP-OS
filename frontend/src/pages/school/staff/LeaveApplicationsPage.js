import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Check, X, AirplaneTilt } from "@phosphor-icons/react";
import { useStaffMeta, LEAVE_STATUS_TONE } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";
const STATUS_FILTERS = ["pending", "approved_l1", "approved", "rejected", "cancelled"];

export default function LeaveApplicationsPage() {
  const { leaveTypes } = useStaffMeta();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("pending");
  const [employees, setEmployees] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ employee_id: "", leave_type_id: "", start_date: "", end_date: "", reason: "", is_half_day: false });

  const load = useCallback(async () => {
    try {
      const p = new URLSearchParams();
      if (status) p.set("status", status);
      const { data } = await api.get(`/school/staff/leave-applications?${p}`);
      setItems(data.items); setTotal(data.total);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [status]);
  const loadEmployees = async () => {
    try { const { data } = await api.get("/school/staff/employees?page_size=200"); setEmployees(data.items || []); }
    catch { /* silent */ }
  };
  useEffect(() => { load(); loadEmployees(); }, [load]);

  const submit = async () => {
    if (!form.employee_id || !form.leave_type_id || !form.start_date || !form.end_date || !form.reason) return toast.error("All fields required");
    try {
      await api.post("/school/staff/leave-applications", form);
      toast.success("Leave applied"); setOpen(false);
      setForm({ employee_id: "", leave_type_id: "", start_date: "", end_date: "", reason: "", is_half_day: false }); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const approve = async (id) => {
    try { await api.post(`/school/staff/leave-applications/${id}/approve`, { reason: "ok" }); toast.success("Approved"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const reject = async (id) => {
    const reason = window.prompt("Rejection reason?") || "";
    try { await api.post(`/school/staff/leave-applications/${id}/reject`, { reason }); toast.success("Rejected"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const cancel = async (id) => {
    if (!window.confirm("Cancel this leave?")) return;
    try { await api.post(`/school/staff/leave-applications/${id}/cancel`); toast.success("Cancelled"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="leave-apps-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Staff Master</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="la-title">Leave applications</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{total} in view · <span className="capitalize">{status.replace("_", " ")}</span></div>
        </div>
        <div className="flex items-center gap-3">
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="rounded-none h-10 w-[160px]" data-testid="la-status-filter"><SelectValue /></SelectTrigger>
            <SelectContent>{STATUS_FILTERS.map(s => <SelectItem key={s} value={s} data-testid={`las-${s}`}>{s.replace("_", " ")}</SelectItem>)}</SelectContent>
          </Select>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild><Button data-testid="btn-apply-leave" className="rounded-full bg-[var(--klein)] text-white"><Plus size={14} className="mr-1"/> Apply leave</Button></DialogTrigger>
            <DialogContent className="rounded-none max-w-md">
              <DialogHeader><DialogTitle>New leave application</DialogTitle></DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label className="overline">Employee</Label>
                  <Select value={form.employee_id} onValueChange={v => setForm({ ...form, employee_id: v })}>
                    <SelectTrigger className="rounded-none h-10 mt-2" data-testid="la-emp"><SelectValue placeholder="Choose employee" /></SelectTrigger>
                    <SelectContent>{employees.map(e => <SelectItem key={e.id} value={e.id}>{e.first_name} {e.last_name || ""} · {e.employee_code}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="overline">Leave type</Label>
                  <Select value={form.leave_type_id} onValueChange={v => setForm({ ...form, leave_type_id: v })}>
                    <SelectTrigger className="rounded-none h-10 mt-2" data-testid="la-type"><SelectValue placeholder="Choose type" /></SelectTrigger>
                    <SelectContent>{leaveTypes.filter(t => t.is_active !== false).map(t => <SelectItem key={t.id} value={t.id}>{t.name} ({t.code})</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><Label className="overline">Start</Label><Input type="date" value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} className={field} data-testid="la-start" /></div>
                  <div><Label className="overline">End</Label><Input type="date" value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} className={field} data-testid="la-end" /></div>
                </div>
                <div><Label className="overline">Reason</Label><Input value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} className={field} data-testid="la-reason" /></div>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_half_day} onChange={e => setForm({ ...form, is_half_day: e.target.checked })} data-testid="la-half" /> Half day</label>
              </div>
              <DialogFooter><Button onClick={submit} data-testid="la-submit" className="rounded-none bg-[var(--klein)] text-white">Apply</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="mt-8 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="la-table">
          <TableHeader><TableRow><TableHead>Employee</TableHead><TableHead>Type</TableHead><TableHead>Dates</TableHead><TableHead>Days</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {items.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="la-empty">No applications in this filter.</TableCell></TableRow>}
            {items.map(l => {
              const emp = employees.find(e => e.id === l.employee_id);
              const lt = leaveTypes.find(t => t.id === l.leave_type_id);
              const canDecide = ["pending", "approved_l1"].includes(l.status);
              const canCancel = ["pending", "approved_l1", "approved"].includes(l.status);
              return (
                <TableRow key={l.id} data-testid={`la-row-${l.id}`}>
                  <TableCell className="font-heading font-semibold"><AirplaneTilt size={14} weight="duotone" className="text-[var(--klein)] inline mr-2"/>{emp ? `${emp.first_name} ${emp.last_name || ""}` : "—"}</TableCell>
                  <TableCell><span className="font-mono text-xs">{lt?.code || "?"}</span></TableCell>
                  <TableCell className="text-xs">{l.start_date?.slice(0, 10)} → {l.end_date?.slice(0, 10)}</TableCell>
                  <TableCell className="font-mono text-xs">{l.days}</TableCell>
                  <TableCell><span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${LEAVE_STATUS_TONE[l.status] || ""}`}>{l.status.replace("_", " ")}</span></TableCell>
                  <TableCell className="text-right space-x-1">
                    {canDecide && <Button size="sm" variant="outline" onClick={() => approve(l.id)} data-testid={`la-approve-${l.id}`} className="rounded-none"><Check size={12} className="mr-1"/> Approve</Button>}
                    {canDecide && <Button size="sm" variant="outline" onClick={() => reject(l.id)} data-testid={`la-reject-${l.id}`} className="rounded-none text-[var(--accent-red)]"><X size={12} className="mr-1"/> Reject</Button>}
                    {canCancel && <Button size="sm" variant="outline" onClick={() => cancel(l.id)} data-testid={`la-cancel-${l.id}`} className="rounded-none">Cancel</Button>}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
