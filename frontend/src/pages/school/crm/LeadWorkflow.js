import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Calendar, LinkSimple, Copy } from "@phosphor-icons/react";

const FLOW = ["NEW_INQUIRY", "CONTACTED", "VISIT_SCHEDULED", "FORM_FILLED", "UNDER_REVIEW", "APPROVED", "FEE_PENDING", "ADMITTED"];
export const MANUAL_STAGES = ["NEW_INQUIRY", "CONTACTED", "VISIT_SCHEDULED", "LOST"];

export function PipelineStrip({ stage, stages }) {
  const label = Object.fromEntries((stages || []).map((s) => [s.code, s.label]));
  const idx = FLOW.indexOf(stage);
  if (stage === "LOST") {
    return <div className="mt-6 border border-[var(--accent-red)] text-[var(--accent-red)] px-3 py-2 text-xs uppercase tracking-widest" data-testid="pipeline-lost">Lost / rejected</div>;
  }
  return (
    <div className="mt-6 flex overflow-x-auto border border-[var(--tinted-grey-200)] bg-white" data-testid="pipeline-strip">
      {FLOW.map((c, i) => (
        <div key={c} data-testid={`pipeline-step-${c}`}
          className={`flex-1 min-w-[110px] px-3 py-2 text-[10px] uppercase tracking-widest border-r last:border-r-0 border-[var(--tinted-grey-200)] transition-colors ${i < idx ? "bg-[var(--klein)]/10 text-[var(--klein)]" : i === idx ? "bg-[var(--klein)] text-white font-bold" : "text-[var(--tinted-grey-400)]"}`}>
          {label[c] || c.replace(/_/g, " ")}
        </div>
      ))}
    </div>
  );
}

export function ScheduleVisitButton({ leadId, onDone }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ scheduled_date: "", start_time: "10:00", end_time: "10:30", expected_visitors: 2, purpose: "Campus tour" });
  const submit = async () => {
    if (!f.scheduled_date) return toast.error("Pick a date");
    try { await api.post("/school/crm/visits", { ...f, lead_id: leadId }); toast.success("Visit scheduled"); setOpen(false); onDone(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const fld = (k, type = "text") => <Input type={type} value={f[k]} onChange={(e) => setF({ ...f, [k]: type === "number" ? Number(e.target.value) : e.target.value })} className="mt-2 rounded-none" data-testid={`visit-${k}`} />;
  return (
    <>
      <Button variant="outline" className="rounded-full" onClick={() => setOpen(true)} data-testid="btn-schedule-visit"><Calendar size={14} className="mr-1" />Schedule visit</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="rounded-none max-w-md" data-testid="schedule-visit-dialog">
          <DialogHeader><DialogTitle>Schedule campus visit</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2"><Label className="overline">Date</Label>{fld("scheduled_date", "date")}</div>
            <div><Label className="overline">Start</Label>{fld("start_time", "time")}</div>
            <div><Label className="overline">End</Label>{fld("end_time", "time")}</div>
            <div><Label className="overline">Visitors</Label>{fld("expected_visitors", "number")}</div>
            <div><Label className="overline">Purpose</Label>{fld("purpose")}</div>
          </div>
          <DialogFooter><Button onClick={submit} className="rounded-none bg-[var(--klein)] text-white" data-testid="visit-submit">Schedule</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function ApplicantLinkButton({ leadId, onDone }) {
  const [link, setLink] = useState(null);
  const create = async () => {
    try { const { data } = await api.post("/school/admissions/applicant-links", { lead_id: leadId }); setLink(data); onDone?.(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const url = link ? `${window.location.origin}${link.url_path}` : "";
  const copy = async () => { try { await navigator.clipboard.writeText(url); toast.success("Link copied"); } catch { toast.error("Copy failed — select and copy manually"); } };
  return (
    <>
      <Button variant="outline" className="rounded-full" onClick={create} data-testid="btn-applicant-link"><LinkSimple size={14} className="mr-1" />Send application link</Button>
      <Dialog open={!!link} onOpenChange={(o) => { if (!o) setLink(null); }}>
        <DialogContent className="rounded-none max-w-lg" data-testid="applicant-link-dialog">
          <DialogHeader><DialogTitle>Secure application link</DialogTitle></DialogHeader>
          <div className="text-sm text-[var(--tinted-grey-500)]">Share this with the parent. They can fill in the form and upload documents without an account. Any earlier link for this application stops working.</div>
          <div className="flex gap-2 mt-2">
            <Input readOnly value={url} className="rounded-none font-mono text-xs" data-testid="applicant-link-url" onFocus={(e) => e.target.select()} />
            <Button onClick={copy} className="rounded-none" data-testid="applicant-link-copy"><Copy size={14} /></Button>
          </div>
          <div className="text-xs text-[var(--tinted-grey-500)]" data-testid="applicant-link-expiry">Expires {link && new Date(link.expires_at).toLocaleDateString()}</div>
        </DialogContent>
      </Dialog>
    </>
  );
}
