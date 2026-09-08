import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle, UploadSimple, Warning, XCircle, GraduationCap, FileText } from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

const NEXT_STATUS_MAP = {
  DRAFT: ["SUBMITTED","WITHDRAWN"],
  SUBMITTED: ["UNDER_REVIEW","DOCUMENTS_PENDING","WITHDRAWN"],
  UNDER_REVIEW: ["APPROVED","REJECTED","DOCUMENTS_PENDING","WITHDRAWN"],
  DOCUMENTS_PENDING: ["UNDER_REVIEW","REJECTED","WITHDRAWN"],
  APPROVED: ["WITHDRAWN"],
  REJECTED: [], WITHDRAWN: [], CONVERTED: [],
};

export default function ApplicationDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [app, setApp] = useState(null);
  const [docs, setDocs] = useState([]);
  const [reviewNotes, setReviewNotes] = useState("");
  const [reason, setReason] = useState("");
  const [nextStatus, setNextStatus] = useState("");
  const fileRef = useRef(null);
  const [uploadType, setUploadType] = useState(null);
  const [rejectDoc, setRejectDoc] = useState(null);
  const [rejectDocReason, setRejectDocReason] = useState("");

  const load = async () => {
    try {
      const [a, d] = await Promise.all([
        api.get(`/school/admissions/applications/${id}`),
        api.get(`/school/admissions/applications/${id}/documents`),
      ]);
      setApp(a.data); setDocs(d.data); setReviewNotes(a.data.review_notes || "");
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const changeStatus = async () => {
    if (!nextStatus) return;
    try {
      await api.post(`/school/admissions/applications/${id}/status`, {
        status: nextStatus, reason: reason || undefined, review_notes: reviewNotes,
      });
      toast.success(`Status → ${nextStatus}`);
      setNextStatus(""); setReason("");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const uploadDoc = async (typeCode, file) => {
    if (!file) return;
    try {
      const fd = new FormData();
      fd.append("type_code", typeCode);
      fd.append("file", file);
      await api.post(`/school/admissions/applications/${id}/documents`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Document uploaded");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setUploadType(null); if (fileRef.current) fileRef.current.value = ""; }
  };

  const verifyDoc = async (docId, status, reason) => {
    try {
      await api.post(`/school/admissions/applications/${id}/documents/${docId}/verify`, { status, rejection_reason: reason || null });
      toast.success(status === "VERIFIED" ? "Document verified" : "Document rejected");
      setRejectDoc(null); setRejectDocReason("");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const convert = async () => {
    try {
      const { data } = await api.post(`/school/admissions/applications/${id}/convert`, { override_docs: false });
      if (data.already_converted) toast.info(`Already converted (student ${data.student_number})`);
      else toast.success(`Converted → Student ${data.student_number}`);
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  if (!app) return <div className="text-[var(--tinted-grey-500)]">Loading…</div>;

  const total = docs.length;
  const required = docs.filter(d => d.type_code); // all seeded
  const verified = docs.filter(d => d.status === "VERIFIED").length;
  const pct = total ? Math.round((verified / total) * 100) : 0;
  const missingVerified = docs.some(d => d.status !== "VERIFIED");

  return (
    <div data-testid="application-detail">
      <button onClick={() => navigate("/school/admissions/applications")} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--tinted-grey-500)] hover:text-[var(--ink)]" data-testid="back-to-apps">
        <ArrowLeft size={14} /> All applications
      </button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="overline mb-2 font-mono">{app.application_number}</div>
          <h1 className="font-heading font-black text-4xl tracking-tighter" data-testid="app-student-name">{app.student_first_name} {app.student_last_name}</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">
            {app.class_requested} · {app.academic_year} · <span data-testid="app-status" className="uppercase tracking-widest">{app.status}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {NEXT_STATUS_MAP[app.status]?.length > 0 && (
            <>
              <Select value={nextStatus} onValueChange={setNextStatus}>
                <SelectTrigger className="rounded-none h-10 w-[200px]" data-testid="app-next-status"><SelectValue placeholder="Change status" /></SelectTrigger>
                <SelectContent>
                  {NEXT_STATUS_MAP[app.status].map(s => <SelectItem key={s} value={s} data-testid={`app-next-${s}`}>{s.replace(/_/g," ")}</SelectItem>)}
                </SelectContent>
              </Select>
              <Button onClick={changeStatus} disabled={!nextStatus} data-testid="app-change-status" className="rounded-full bg-[var(--ink)] hover:bg-[var(--klein)] text-white transition-colors">Apply</Button>
            </>
          )}
          {app.status === "APPROVED" && (
            <Button onClick={convert} data-testid="app-convert" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><GraduationCap size={14} className="mr-1" /> Convert to student</Button>
          )}
          {app.status === "CONVERTED" && (
            <div className="text-xs uppercase tracking-widest text-[var(--klein)]" data-testid="app-converted-badge">
              <CheckCircle size={14} className="inline mr-1" /> Converted · student #{app.student_id?.slice(-6)}
            </div>
          )}
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Details */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-white border border-[var(--tinted-grey-200)] p-5">
            <div className="overline mb-3">Applicant</div>
            <div className="font-heading font-bold">{app.student_first_name} {app.student_last_name}</div>
            <div className="text-sm text-[var(--tinted-grey-500)]">{app.student_dob || "—"} · {app.student_gender || "—"}</div>
            <div className="mt-2 text-sm">{app.previous_school || "First-time admission"}</div>
          </div>
          <div className="bg-white border border-[var(--tinted-grey-200)] p-5">
            <div className="overline mb-3">Parent</div>
            <div className="font-heading font-bold">{app.parent_name}</div>
            <div className="text-sm">{app.parent_mobile}</div>
            {app.parent_email && <div className="text-sm">{app.parent_email}</div>}
          </div>
          <div className="bg-white border border-[var(--tinted-grey-200)] p-5">
            <div className="overline mb-2">Review notes</div>
            <Textarea rows={4} value={reviewNotes} onChange={(e) => setReviewNotes(e.target.value)} className="rounded-none focus-visible:ring-0 focus-visible:border-[var(--klein)]" data-testid="review-notes" />
            {app.status === "REJECTED" && app.rejection_reason && <div className="mt-3 text-sm text-[var(--accent-red)]" data-testid="app-rejection-reason">Reason: {app.rejection_reason}</div>}
            {nextStatus === "REJECTED" && (
              <div className="mt-3">
                <label className="overline">Rejection reason (required)</label>
                <Textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} className="mt-2 rounded-none focus-visible:ring-0 focus-visible:border-[var(--klein)]" data-testid="reject-reason-input" />
              </div>
            )}
          </div>
        </div>

        {/* Right: Documents */}
        <div className="lg:col-span-8">
          <div className="bg-white border border-[var(--tinted-grey-200)] p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="overline">Document checklist</div>
                <div className="font-heading font-bold text-xl">{verified}/{total} verified</div>
              </div>
              <div className="text-right">
                <div className="font-heading font-black text-2xl tabular" data-testid="doc-completion">{pct}%</div>
                <div className="text-xs text-[var(--tinted-grey-500)]">complete</div>
              </div>
            </div>
            <div className="h-1.5 bg-[var(--tinted-grey-100)] mb-6"><div className="h-full bg-[var(--klein)] transition-all" style={{ width: `${pct}%` }} /></div>

            <div className="divide-y divide-[var(--tinted-grey-200)]" data-testid="documents-list">
              {docs.length === 0 && <div className="p-4 text-sm text-[var(--tinted-grey-500)]">No documents required.</div>}
              {docs.map(d => (
                <div key={d.id} className="py-3 flex items-center justify-between gap-2" data-testid={`doc-row-${d.type_code}`}>
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText size={18} weight="duotone" className="text-[var(--klein)] shrink-0" />
                    <div className="min-w-0">
                      <div className="font-heading font-semibold">{d.type_label}</div>
                      <div className="text-xs text-[var(--tinted-grey-500)] truncate">{d.filename || "Not uploaded"} {d.size_bytes ? `· ${(d.size_bytes/1024).toFixed(0)} KB` : ""}</div>
                      {d.status === "REJECTED" && d.rejection_reason && <div className="text-xs text-[var(--accent-red)] mt-0.5">Rejected: {d.rejection_reason}</div>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusBadge status={d.status} />
                    <label className="cursor-pointer" data-testid={`doc-upload-${d.type_code}`}>
                      <input type="file" className="hidden" onChange={(e) => uploadDoc(d.type_code, e.target.files?.[0])} />
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-1 border border-[var(--tinted-grey-300)] hover:border-[var(--ink)]"><UploadSimple size={12} /> Upload</span>
                    </label>
                    {d.filename && d.status === "PENDING" && (
                      <>
                        <Button size="sm" variant="outline" onClick={() => verifyDoc(d.id, "VERIFIED")} data-testid={`doc-verify-${d.type_code}`} className="h-8"><CheckCircle size={12} className="mr-1" />Verify</Button>
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button size="sm" variant="outline" data-testid={`doc-reject-${d.type_code}`} className="h-8"><XCircle size={12} className="mr-1" />Reject</Button>
                          </DialogTrigger>
                          <DialogContent className="rounded-none max-w-sm">
                            <DialogHeader><DialogTitle>Reject document</DialogTitle></DialogHeader>
                            <Textarea rows={3} placeholder="Reason (required)" value={rejectDocReason} onChange={(e) => setRejectDocReason(e.target.value)} data-testid="doc-reject-reason" className="rounded-none" />
                            <DialogFooter>
                              <Button onClick={() => verifyDoc(d.id, "REJECTED", rejectDocReason)} data-testid="doc-reject-confirm" disabled={!rejectDocReason.trim()} className="rounded-none bg-[var(--accent-red)] hover:opacity-90 text-white">Reject</Button>
                            </DialogFooter>
                          </DialogContent>
                        </Dialog>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {missingVerified && app.status === "UNDER_REVIEW" && (
              <div className="mt-4 flex items-center gap-2 text-xs text-[var(--tinted-grey-500)]" data-testid="docs-warning">
                <Warning size={14} weight="fill" className="text-[var(--accent-yellow)]" />
                Approving requires all required documents verified (or admission.override permission).
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const color = status === "VERIFIED" ? "var(--klein)" : status === "REJECTED" ? "var(--accent-red)" : status === "NOT_REQUIRED" ? "var(--tinted-grey-400)" : "var(--accent-yellow)";
  return (
    <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-widest px-2 py-0.5" style={{ backgroundColor: color, color: status === "VERIFIED" || status === "REJECTED" ? "white" : "var(--ink)" }}>
      {status.replace(/_/g," ")}
    </span>
  );
}
