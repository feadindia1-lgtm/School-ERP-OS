import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MagnifyingGlass, Plus, CaretLeft, CaretRight, User } from "@phosphor-icons/react";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";
const RELATIONSHIPS = ["father", "mother", "guardian", "legal_guardian", "step_parent", "grandparent", "sibling", "other"];
const PAGE_SIZE = 25;

export default function GuardiansPage() {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ first_name: "", last_name: "", relationship_type: "guardian", mobile_primary: "", email: "", occupation: "" });

  const load = useCallback(async () => {
    try {
      const p = new URLSearchParams();
      if (q) p.set("q", q);
      p.set("page", String(page));
      p.set("page_size", String(PAGE_SIZE));
      const { data } = await api.get(`/school/guardians?${p}`);
      setRows(data.items || []); setTotal(data.total || 0);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [q, page]);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    if (!form.first_name || !form.mobile_primary) return toast.error("First name and mobile are required");
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ""));
      await api.post("/school/guardians", payload);
      toast.success("Guardian created");
      setOpen(false);
      setForm({ first_name: "", last_name: "", relationship_type: "guardian", mobile_primary: "", email: "", occupation: "" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div data-testid="guardians-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Student Master</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="guardians-title">Guardians</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{total} guardian{total === 1 ? "" : "s"}</div>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="btn-new-guardian" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> New guardian</Button>
          </DialogTrigger>
          <DialogContent className="rounded-none max-w-lg">
            <DialogHeader><DialogTitle>New guardian</DialogTitle></DialogHeader>
            <div className="grid grid-cols-2 gap-4">
              <div><Label className="overline">First name</Label><Input value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} className={field} data-testid="g-first" /></div>
              <div><Label className="overline">Last name</Label><Input value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} className={field} data-testid="g-last" /></div>
              <div><Label className="overline">Relationship</Label>
                <Select value={form.relationship_type} onValueChange={v => setForm({ ...form, relationship_type: v })}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="g-rel"><SelectValue /></SelectTrigger>
                  <SelectContent>{RELATIONSHIPS.map(r => <SelectItem key={r} value={r} data-testid={`gr-${r}`}>{r}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="overline">Mobile</Label><Input value={form.mobile_primary} onChange={e => setForm({ ...form, mobile_primary: e.target.value })} className={field} data-testid="g-mobile" /></div>
              <div className="col-span-2"><Label className="overline">Email</Label><Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className={field} data-testid="g-email" /></div>
              <div className="col-span-2"><Label className="overline">Occupation</Label><Input value={form.occupation} onChange={e => setForm({ ...form, occupation: e.target.value })} className={field} data-testid="g-occ" /></div>
            </div>
            <DialogFooter><Button onClick={submit} data-testid="g-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-6 relative max-w-md">
        <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tinted-grey-400)]" />
        <Input value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => { if (e.key === "Enter") { setPage(1); load(); } }} placeholder="Search name, mobile, email" className="pl-9 h-11 rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)]" data-testid="guardians-search" />
      </div>

      <div className="mt-6 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="guardians-table">
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Relationship</TableHead>
              <TableHead>Mobile</TableHead>
              <TableHead>Email</TableHead>
              <TableHead className="text-right">Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow><TableCell colSpan={5} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="guardians-empty">No guardians match.</TableCell></TableRow>
            )}
            {rows.map(g => (
              <TableRow key={g.id} data-testid={`guardian-row-${g.id}`} className="hover:bg-[var(--tinted-grey-100)] transition-colors">
                <TableCell className="font-heading font-semibold">
                  <Link to={`/school/guardians/${g.id}`} className="flex items-center gap-2">
                    <User size={14} weight="duotone" className="text-[var(--klein)]" />
                    {g.first_name} {g.last_name || ""}
                  </Link>
                </TableCell>
                <TableCell className="capitalize">{g.relationship_type}</TableCell>
                <TableCell className="font-mono text-xs">{g.mobile_primary}</TableCell>
                <TableCell className="font-mono text-xs">{g.email || "—"}</TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">{new Date(g.created_at).toISOString().slice(0, 10)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <div className="text-[var(--tinted-grey-500)]" data-testid="g-page-info">Page {page} of {totalPages} · {total} total</div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} data-testid="g-page-prev" className="rounded-none"><CaretLeft size={14} /> Prev</Button>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} data-testid="g-page-next" className="rounded-none">Next <CaretRight size={14} /></Button>
          </div>
        </div>
      )}
    </div>
  );
}
