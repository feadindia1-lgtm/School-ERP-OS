import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Coins, CheckCircle } from "@phosphor-icons/react";

export function FeePanel({ app, onChanged }) {
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  if (!app.fee_status) return null;
  const received = app.fee_status === "received";
  const mark = async (status) => {
    try {
      await api.post(`/school/admissions/applications/${app.id}/fee-status`, { status, reference: reference || null, note: note || null });
      toast.success(status === "received" ? "Fee marked as received" : "Fee set back to pending");
      setReference(""); setNote(""); onChanged();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  return (
    <div className={`border p-5 ${received ? "border-emerald-600 bg-emerald-50" : "border-amber-300 bg-amber-50"}`} data-testid="fee-panel">
      <div className="overline mb-2 flex items-center gap-2"><Coins size={12} />Admission fee</div>
      <div className="font-heading font-bold" data-testid="fee-status">{received ? "Received" : "Pending"}</div>
      {received ? (
        <div className="text-xs mt-1 space-y-2">
          <div>Reference: <span className="font-mono" data-testid="fee-reference">{app.fee_reference}</span></div>
          {app.fee_note && <div>{app.fee_note}</div>}
          {app.status === "APPROVED" && <Button size="sm" variant="outline" className="rounded-none" onClick={() => mark("pending")} data-testid="fee-mark-pending">Undo</Button>}
        </div>
      ) : app.status === "APPROVED" ? (
        <div className="mt-3 space-y-2">
          <div className="text-xs text-[var(--tinted-grey-500)]">Record the receipt number once the fee is paid. Payment collection itself is handled outside this screen.</div>
          <Input placeholder="Receipt / reference no." value={reference} onChange={(e) => setReference(e.target.value)} className="rounded-none bg-white" data-testid="fee-reference-input" />
          <Input placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} className="rounded-none bg-white" data-testid="fee-note-input" />
          <Button size="sm" disabled={!reference.trim()} onClick={() => mark("received")} className="rounded-none bg-[var(--ink)] text-white" data-testid="fee-mark-received"><CheckCircle size={14} className="mr-1" />Mark fee received</Button>
        </div>
      ) : null}
    </div>
  );
}

export function ApplicantExtras({ app }) {
  const answers = Object.entries(app.form_answers || {});
  if (!app.address && answers.length === 0 && app.submitted_via === "staff") return null;
  return (
    <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="applicant-extras">
      <div className="overline mb-3">From the applicant</div>
      <div className="text-xs text-[var(--tinted-grey-500)] mb-2" data-testid="app-submitted-via">Source: {app.submitted_via.replace(/_/g, " ")}</div>
      {app.address && <div className="text-sm mb-2">{app.address}</div>}
      {answers.map(([k, v]) => <div key={k} className="text-sm"><span className="font-mono text-xs text-[var(--tinted-grey-500)]">{k}</span> · {v}</div>)}
    </div>
  );
}
