import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Calendar, CheckCircle, Archive } from "@phosphor-icons/react";
import { useAcademicYears, BOARD_PRESETS_LIST, ACADEMIC_STATUS_TONE } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function AcademicYearsPage() {
  const { years, reload } = useAcademicYears();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", start_date: "", end_date: "", board_preset: "CBSE", is_current: false });

  const submit = async () => {
    if (!form.name || !form.start_date || !form.end_date) return toast.error("All fields required");
    try {
      await api.post("/school/academic/years", form);
      toast.success("Year created"); setOpen(false);
      setForm({ name: "", start_date: "", end_date: "", board_preset: "CBSE", is_current: false });
      reload();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const setCurrent = async (id) => {
    try { await api.post(`/school/academic/years/${id}/set-current`); toast.success("Set as current"); reload(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const archive = async (id) => {
    if (!window.confirm("Archive this year? It becomes read-only.")) return;
    try { await api.post(`/school/academic/years/${id}/archive`); toast.success("Archived"); reload(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="academic-years-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Academic Framework</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="years-title">Academic years</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{years.length} year{years.length === 1 ? "" : "s"} · promotion-ready timeline</div>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="btn-new-year" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> New year</Button>
          </DialogTrigger>
          <DialogContent className="rounded-none max-w-md">
            <DialogHeader><DialogTitle>New academic year</DialogTitle></DialogHeader>
            <div className="space-y-4">
              <div><Label className="overline">Name</Label><Input placeholder="e.g. 2026-27" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className={field} data-testid="yr-name" /></div>
              <div className="grid grid-cols-2 gap-4">
                <div><Label className="overline">Start</Label><Input type="date" value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} className={field} data-testid="yr-start" /></div>
                <div><Label className="overline">End</Label><Input type="date" value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} className={field} data-testid="yr-end" /></div>
              </div>
              <div><Label className="overline">Board preset</Label>
                <Select value={form.board_preset} onValueChange={v => setForm({ ...form, board_preset: v })}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="yr-board"><SelectValue /></SelectTrigger>
                  <SelectContent>{BOARD_PRESETS_LIST.map(b => <SelectItem key={b} value={b} data-testid={`yb-${b}`}>{b}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_current} onChange={e => setForm({ ...form, is_current: e.target.checked })} data-testid="yr-current" />
                Set as current immediately
              </label>
            </div>
            <DialogFooter><Button onClick={submit} data-testid="yr-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-8 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="years-table">
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Board</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Terms</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {years.length === 0 && (
              <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="years-empty">
                No academic years yet. Create one to unlock classes, sections and the school calendar.
              </TableCell></TableRow>
            )}
            {years.map(y => (
              <TableRow key={y.id} data-testid={`year-row-${y.id}`} className="hover:bg-[var(--tinted-grey-100)] transition-colors">
                <TableCell className="font-heading font-semibold">
                  <div className="flex items-center gap-2">
                    <Calendar size={14} weight="duotone" className="text-[var(--klein)]" />
                    {y.name}
                  </div>
                </TableCell>
                <TableCell className="font-mono text-xs">{y.board_preset}</TableCell>
                <TableCell className="text-xs font-mono">{y.start_date?.slice(0,10)} → {y.end_date?.slice(0,10)}</TableCell>
                <TableCell>
                  <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${ACADEMIC_STATUS_TONE[y.status] || ""}`} data-testid={`year-status-${y.id}`}>{y.status}</span>
                </TableCell>
                <TableCell className="text-xs">{(y.term_names || []).join(", ") || "—"}</TableCell>
                <TableCell className="text-right space-x-2">
                  {!y.is_current && y.status !== "archived" && (
                    <Button size="sm" variant="outline" onClick={() => setCurrent(y.id)} data-testid={`btn-set-current-${y.id}`} className="rounded-none">
                      <CheckCircle size={12} className="mr-1"/> Set current
                    </Button>
                  )}
                  {y.status !== "archived" && !y.is_current && (
                    <Button size="sm" variant="outline" onClick={() => archive(y.id)} data-testid={`btn-archive-${y.id}`} className="rounded-none">
                      <Archive size={12} className="mr-1"/> Archive
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
