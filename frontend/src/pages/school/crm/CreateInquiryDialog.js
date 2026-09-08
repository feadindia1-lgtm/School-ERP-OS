import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { WarningOctagon } from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Link } from "react-router-dom";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

const empty = {
  student_first_name: "", student_last_name: "", student_dob: "",
  class_seeking: "", academic_year: "",
  parent_name: "", parent_mobile: "", parent_email: "",
  source: "website", priority: "medium", notes: "",
};

export default function CreateInquiryDialog({ open, onOpenChange, settings, onCreated }) {
  const [form, setForm] = useState(empty);
  const [busy, setBusy] = useState(false);
  const [dups, setDups] = useState([]);
  const set = (k) => (v) => setForm(f => ({ ...f, [k]: v.target ? v.target.value : v }));

  useEffect(() => { if (!open) { setForm(empty); setDups([]); } }, [open]);

  useEffect(() => {
    if (!open) return;
    if (!form.parent_mobile && !form.parent_email) { setDups([]); return; }
    const t = setTimeout(async () => {
      try {
        const params = new URLSearchParams();
        if (form.parent_mobile) params.set("parent_mobile", form.parent_mobile);
        if (form.parent_email) params.set("parent_email", form.parent_email);
        if (form.student_first_name && form.student_last_name && form.student_dob) {
          params.set("student_first_name", form.student_first_name);
          params.set("student_last_name", form.student_last_name);
          params.set("student_dob", form.student_dob);
        }
        const { data } = await api.get(`/school/crm/leads/check-duplicate?${params.toString()}`);
        setDups(data.duplicates);
      } catch {}
    }, 350);
    return () => clearTimeout(t);
  }, [open, form.parent_mobile, form.parent_email, form.student_dob, form.student_first_name, form.student_last_name]);

  const submit = async (force = false) => {
    setBusy(true);
    try {
      // Strip empty-string optional fields so Pydantic EmailStr/date validators
      // don't reject "" — send omitted (falsy) instead.
      const payload = Object.fromEntries(
        Object.entries(form).filter(([, v]) => v !== "" && v !== null && v !== undefined),
      );
      await api.post("/school/crm/leads", { ...payload, force });
      toast.success("Inquiry created");
      onOpenChange(false);
      onCreated?.();
    } catch (e) {
      const detail = e?.response?.data?.error?.details || e?.response?.data?.error;
      if (detail?.code === "duplicate_lead") {
        toast.error("Possible existing inquiry — review below then click 'Create anyway'");
      } else {
        toast.error(formatApiError(e));
      }
    } finally { setBusy(false); }
  };

  const sources = settings?.sources || ["website","walk_in","phone","whatsapp","referral","other"];
  const priorities = settings?.priorities || ["low","medium","high","urgent"];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-none max-w-2xl" data-testid="create-inquiry-dialog">
        <DialogHeader><DialogTitle className="font-heading tracking-tight">New inquiry</DialogTitle></DialogHeader>

        {dups.length > 0 && (
          <div className="border-l-2 border-[var(--accent-yellow)] bg-[var(--accent-yellow)]/10 p-4" data-testid="duplicate-warning">
            <div className="flex items-center gap-2 mb-2">
              <WarningOctagon size={16} weight="fill" className="text-[var(--accent-yellow)]" />
              <div className="font-heading font-bold">Possible existing inquiry</div>
            </div>
            <ul className="space-y-1 text-sm">
              {dups.map(d => (
                <li key={d.id} data-testid={`dup-${d.inquiry_number}`}>
                  <Link className="klein-underline text-[var(--klein)] font-mono" to={`/school/admissions/inquiries/${d.id}`}>{d.inquiry_number}</Link>{" — "}
                  {d.student_first_name} {d.student_last_name} · {d.parent_name} · {d.parent_mobile}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div><Label className="overline">Student first name</Label><Input required value={form.student_first_name} onChange={set("student_first_name")} className={field} data-testid="inq-student-first" /></div>
          <div><Label className="overline">Student last name</Label><Input required value={form.student_last_name} onChange={set("student_last_name")} className={field} data-testid="inq-student-last" /></div>
          <div><Label className="overline">Date of birth</Label><Input type="date" value={form.student_dob} onChange={set("student_dob")} className={field} data-testid="inq-student-dob" /></div>
          <div><Label className="overline">Class seeking</Label><Input value={form.class_seeking} onChange={set("class_seeking")} placeholder="Grade 1" className={field} data-testid="inq-class" /></div>
          <div><Label className="overline">Academic year</Label><Input value={form.academic_year} onChange={set("academic_year")} placeholder="AY 2026-27" className={field} data-testid="inq-ay" /></div>
          <div><Label className="overline">Parent name</Label><Input required value={form.parent_name} onChange={set("parent_name")} className={field} data-testid="inq-parent-name" /></div>
          <div><Label className="overline">Parent mobile</Label><Input required value={form.parent_mobile} onChange={set("parent_mobile")} className={field} data-testid="inq-parent-mobile" /></div>
          <div><Label className="overline">Parent email</Label><Input type="email" value={form.parent_email} onChange={set("parent_email")} className={field} data-testid="inq-parent-email" /></div>
          <div>
            <Label className="overline">Source</Label>
            <Select value={form.source} onValueChange={set("source")}>
              <SelectTrigger className="mt-2 rounded-none h-10 border-x-0 border-t-0 border-b-2 border-[var(--ink)]" data-testid="inq-source"><SelectValue /></SelectTrigger>
              <SelectContent>
                {sources.map(s => <SelectItem key={s} value={s} data-testid={`inq-source-${s}`}>{s.replace(/_/g," ")}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="overline">Priority</Label>
            <Select value={form.priority} onValueChange={set("priority")}>
              <SelectTrigger className="mt-2 rounded-none h-10 border-x-0 border-t-0 border-b-2 border-[var(--ink)]" data-testid="inq-priority"><SelectValue /></SelectTrigger>
              <SelectContent>
                {priorities.map(p => <SelectItem key={p} value={p} data-testid={`inq-priority-${p}`}>{p}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="md:col-span-2"><Label className="overline">Notes</Label><Textarea rows={2} value={form.notes} onChange={set("notes")} className="mt-2 rounded-none focus-visible:ring-0 focus-visible:border-[var(--klein)]" data-testid="inq-notes" /></div>
        </div>

        <DialogFooter>
          {dups.length > 0 ? (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button data-testid="inq-create-anyway" onClick={() => submit(true)} disabled={busy} className="bg-[var(--accent-yellow)] text-[var(--ink)] hover:opacity-90">
                {busy ? "Creating…" : "Create anyway"}
              </Button>
            </>
          ) : (
            <Button data-testid="inq-submit" onClick={() => submit(false)} disabled={busy} className="rounded-none bg-[var(--klein)] hover:opacity-90 text-white transition-opacity">
              {busy ? "Creating…" : "Create inquiry"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
