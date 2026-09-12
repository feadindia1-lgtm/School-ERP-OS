import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash, AirplaneTilt } from "@phosphor-icons/react";
import { LEAVE_APPLICABLE_TO, LEAVE_ACCRUAL_FREQ } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function LeaveTypesPage() {
  const [items, setItems] = useState([]);
  const [presets, setPresets] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", max_per_year: 12, approval_steps: 1, accrual_frequency: "yearly", applicable_to: "all", is_paid: true, requires_document: false, carry_forward: false });

  const load = async () => {
    try { const { data } = await api.get("/school/staff/leave-types"); setItems(data.items); setPresets(data.presets || []); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); }, []);

  const applyPreset = (code) => {
    const p = presets.find(x => x.code === code);
    if (!p) return;
    setForm({ ...form, ...p });
  };

  const submit = async () => {
    if (!form.name || !form.code) return toast.error("Name & code required");
    try {
      await api.post("/school/staff/leave-types", form);
      toast.success("Leave type created"); setOpen(false);
      setForm({ name: "", code: "", max_per_year: 12, approval_steps: 1, accrual_frequency: "yearly", applicable_to: "all", is_paid: true, requires_document: false, carry_forward: false });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const del = async (id) => {
    if (!window.confirm("Delete this leave type?")) return;
    try { await api.delete(`/school/staff/leave-types/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const patchActive = async (id, is_active) => {
    try { await api.patch(`/school/staff/leave-types/${id}`, { is_active }); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="leave-types-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Staff Master</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="lt-title">Leave types</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{items.length} type{items.length === 1 ? "" : "s"} · seed from presets or fully custom</div>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button data-testid="btn-new-leave-type" className="rounded-full bg-[var(--klein)] text-white"><Plus size={14} className="mr-1"/> New type</Button></DialogTrigger>
          <DialogContent className="rounded-none max-w-lg">
            <DialogHeader><DialogTitle>New leave type</DialogTitle></DialogHeader>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label className="overline">Start from preset</Label>
                <Select value="" onValueChange={applyPreset}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="lt-preset"><SelectValue placeholder="Optional — populates fields" /></SelectTrigger>
                  <SelectContent>{presets.map(p => <SelectItem key={p.code} value={p.code} data-testid={`ltp-${p.code}`}>{p.name} ({p.code})</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="overline">Name</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className={field} data-testid="lt-name" /></div>
              <div><Label className="overline">Code</Label><Input value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} className={field} data-testid="lt-code" /></div>
              <div><Label className="overline">Max per year</Label><Input type="number" value={form.max_per_year || 0} onChange={e => setForm({ ...form, max_per_year: parseFloat(e.target.value || "0") })} className={field} data-testid="lt-max" /></div>
              <div><Label className="overline">Approval steps</Label>
                <Select value={String(form.approval_steps)} onValueChange={v => setForm({ ...form, approval_steps: parseInt(v) })}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="lt-steps"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="1">1 – HR only</SelectItem><SelectItem value="2">2 – Manager + HR</SelectItem></SelectContent>
                </Select>
              </div>
              <div><Label className="overline">Accrual</Label>
                <Select value={form.accrual_frequency} onValueChange={v => setForm({ ...form, accrual_frequency: v })}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="lt-accrual"><SelectValue /></SelectTrigger>
                  <SelectContent>{LEAVE_ACCRUAL_FREQ.map(x => <SelectItem key={x} value={x}>{x}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="overline">Applicable to</Label>
                <Select value={form.applicable_to} onValueChange={v => setForm({ ...form, applicable_to: v })}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="lt-apply"><SelectValue /></SelectTrigger>
                  <SelectContent>{LEAVE_APPLICABLE_TO.map(x => <SelectItem key={x} value={x}>{x.replace("_", " ")}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_paid} onChange={e => setForm({ ...form, is_paid: e.target.checked })} data-testid="lt-paid" /> Paid</label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.requires_document} onChange={e => setForm({ ...form, requires_document: e.target.checked })} data-testid="lt-doc" /> Requires document</label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.carry_forward} onChange={e => setForm({ ...form, carry_forward: e.target.checked })} data-testid="lt-cf" /> Carry forward</label>
            </div>
            <DialogFooter><Button onClick={submit} data-testid="lt-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-8 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="lt-table">
          <TableHeader><TableRow><TableHead>Code</TableHead><TableHead>Name</TableHead><TableHead>Max/yr</TableHead><TableHead>Approval</TableHead><TableHead>Applies to</TableHead><TableHead>Paid</TableHead><TableHead>Active</TableHead><TableHead className="text-right"></TableHead></TableRow></TableHeader>
          <TableBody>
            {items.length === 0 && <TableRow><TableCell colSpan={8} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="lt-empty">No leave types yet — pick a preset to bootstrap.</TableCell></TableRow>}
            {items.map(l => (
              <TableRow key={l.id} data-testid={`lt-row-${l.id}`}>
                <TableCell className="font-mono text-xs">{l.code}</TableCell>
                <TableCell className="font-heading font-semibold"><AirplaneTilt size={14} weight="duotone" className="text-[var(--klein)] inline mr-2"/>{l.name}</TableCell>
                <TableCell>{l.max_per_year ?? "∞"}</TableCell>
                <TableCell>{l.approval_steps === 2 ? "2-step" : "1-step"}</TableCell>
                <TableCell className="capitalize">{(l.applicable_to || "").replace("_", " ")}</TableCell>
                <TableCell>{l.is_paid ? "Yes" : "No"}</TableCell>
                <TableCell><input type="checkbox" checked={l.is_active !== false} onChange={e => patchActive(l.id, e.target.checked)} data-testid={`lt-active-${l.id}`} /></TableCell>
                <TableCell className="text-right"><button onClick={() => del(l.id)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)]" data-testid={`lt-del-${l.id}`}><Trash size={14}/></button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
