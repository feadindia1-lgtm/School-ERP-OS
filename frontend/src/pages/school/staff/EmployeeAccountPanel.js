import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Key, LinkSimple, LinkBreak, UserPlus } from "@phosphor-icons/react";

const ROLE_LABEL = (r) => (r || "").replace(/_/g, " ");

function CreateLoginDialog({ eid, info, emp, open, onOpenChange, onDone }) {
  const [form, setForm] = useState({ email: emp.email_personal || "", password: "", role: info.default_role });
  const submit = async () => {
    try {
      await api.post(`/school/staff/employees/${eid}/account/create`, form);
      toast.success("Login created and linked"); onOpenChange(false); onDone();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-none max-w-md" data-testid="create-login-dialog">
        <DialogHeader><DialogTitle>Create login for {emp.first_name}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div><Label className="overline">Login email</Label><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="mt-2 rounded-none" data-testid="cl-email" /></div>
          <div><Label className="overline">Temporary password (min 8)</Label><Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="mt-2 rounded-none" data-testid="cl-password" /></div>
          <div>
            <Label className="overline">Role</Label>
            <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
              <SelectTrigger className="mt-2 rounded-none" data-testid="cl-role"><SelectValue /></SelectTrigger>
              <SelectContent>{info.assignable_roles.map((r) => <SelectItem key={r} value={r} data-testid={`cl-role-${r}`}>{ROLE_LABEL(r)}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter><Button onClick={submit} className="rounded-none bg-[var(--klein)] text-white" data-testid="cl-submit">Create & link</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function LinkedView({ info, onUnlink }) {
  const u = info.linked_user;
  return (
    <div className="flex items-center justify-between flex-wrap gap-3" data-testid="account-linked">
      <div className="text-sm">
        <div className="font-mono text-xs" data-testid="account-email">{u.email}</div>
        <div className="text-[var(--tinted-grey-500)] text-xs">
          <span className="capitalize">{ROLE_LABEL(u.role)} · {u.status}</span> · {info.teacher_assignment_count} teacher assignment(s)
        </div>
      </div>
      <Button variant="outline" size="sm" className="rounded-none" onClick={onUnlink} data-testid="btn-unlink-account"><LinkBreak size={14} className="mr-1" />Unlink</Button>
    </div>
  );
}

function UnlinkedView({ info, onLink, onCreate }) {
  return (
    <div className="space-y-3" data-testid="account-unlinked">
      <div className="text-sm text-[var(--tinted-grey-500)]">No login linked. Teachers need a login to appear in Teacher Assignments and the timetable.</div>
      {info.suggestions.map((s) => (
        <div key={s.id} className="flex items-center justify-between border border-[var(--tinted-grey-200)] px-3 py-2 text-sm" data-testid={`account-suggestion-${s.id}`}>
          <div><span className="font-mono text-xs">{s.email}</span> <span className="text-[var(--tinted-grey-500)] text-xs">· {s.full_name} · {ROLE_LABEL(s.role)}</span></div>
          <Button size="sm" variant="outline" className="rounded-none" onClick={() => onLink(s.id)} data-testid={`btn-link-${s.id}`}><LinkSimple size={14} className="mr-1" />Link</Button>
        </div>
      ))}
      <Button size="sm" className="rounded-full bg-[var(--klein)] text-white" onClick={onCreate} data-testid="btn-create-login"><UserPlus size={14} className="mr-1" />Create new login</Button>
    </div>
  );
}

export function EmployeeAccountPanel({ emp, onChanged }) {
  const [info, setInfo] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const load = async () => {
    try { const { data } = await api.get(`/school/staff/employees/${emp.id}/account`); setInfo(data); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [emp.id]);
  const done = () => { load(); onChanged?.(); };
  const link = async (uid) => {
    try { await api.post(`/school/staff/employees/${emp.id}/account/link`, { user_id: uid }); toast.success("Login linked"); done(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const unlink = async () => {
    if (!window.confirm("Unlink this login from the employee? The login itself is kept.")) return;
    try { await api.post(`/school/staff/employees/${emp.id}/account/unlink`); toast.success("Unlinked"); done(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  return (
    <div className="bg-white border border-[var(--tinted-grey-200)] p-5 mt-6" data-testid="employee-account-panel">
      <div className="overline mb-3 flex items-center gap-2"><Key size={12} />Login account</div>
      {!info ? <div className="text-sm text-[var(--tinted-grey-500)]">Loading…</div>
        : info.linked_user ? <LinkedView info={info} onUnlink={unlink} />
        : <UnlinkedView info={info} onLink={link} onCreate={() => setCreateOpen(true)} />}
      {info && !info.linked_user && createOpen && (
        <CreateLoginDialog eid={emp.id} info={info} emp={emp} open={createOpen} onOpenChange={setCreateOpen} onDone={done} />
      )}
    </div>
  );
}
