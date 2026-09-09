import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Users } from "@phosphor-icons/react";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function FamiliesPage() {
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ family_name: "", notes: "" });

  const load = async () => {
    try { const { data } = await api.get("/school/families"); setRows(data); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!form.family_name) return toast.error("Family name is required");
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ""));
      await api.post("/school/families", payload);
      toast.success("Family created"); setOpen(false); setForm({ family_name: "", notes: "" }); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="families-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Student Master</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="families-title">Families</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{rows.length} family group{rows.length === 1 ? "" : "s"} · sibling & fee-scope container</div>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="btn-new-family" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> New family</Button>
          </DialogTrigger>
          <DialogContent className="rounded-none max-w-md">
            <DialogHeader><DialogTitle>New family</DialogTitle></DialogHeader>
            <div className="space-y-4">
              <div><Label className="overline">Family name</Label><Input value={form.family_name} onChange={e => setForm({ ...form, family_name: e.target.value })} className={field} data-testid="f-name" /></div>
              <div><Label className="overline">Notes</Label><Input value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} className={field} data-testid="f-notes" /></div>
            </div>
            <DialogFooter><Button onClick={submit} data-testid="f-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-8 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="families-table">
          <TableHeader>
            <TableRow>
              <TableHead>Family name</TableHead>
              <TableHead>Notes</TableHead>
              <TableHead className="text-right">Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow><TableCell colSpan={3} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="families-empty">
                No family groups yet. Create one to link siblings under a shared fee/communication scope.
              </TableCell></TableRow>
            )}
            {rows.map(f => (
              <TableRow key={f.id} data-testid={`family-row-${f.id}`} className="hover:bg-[var(--tinted-grey-100)] transition-colors">
                <TableCell className="font-heading font-semibold">
                  <Link to={`/school/families/${f.id}`} className="flex items-center gap-2 klein-underline">
                    <Users size={14} weight="duotone" className="text-[var(--klein)]" />
                    {f.family_name}
                  </Link>
                </TableCell>
                <TableCell className="text-sm text-[var(--tinted-grey-500)]">{f.notes || "—"}</TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">{new Date(f.created_at).toISOString().slice(0, 10)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
