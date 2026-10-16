import { useCallback, useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { CheckCircle, FileText, UploadSimple, Warning } from "@phosphor-icons/react";
import { ApplicantFormFields, ApplyShell, EMPTY_FORM, toPayload } from "./ApplicantFormFields";

const DOC_TONE = { VERIFIED: "bg-[var(--klein)] text-white", REJECTED: "bg-[var(--accent-red)] text-white", PENDING: "bg-[var(--tinted-grey-100)]" };

function DocRow({ d, canUpload, onUpload }) {
  const uploaded = !!d.filename;
  return (
    <div className="py-3 flex items-center justify-between gap-3 border-b border-[var(--tinted-grey-200)] last:border-0" data-testid={`ap-doc-${d.type_code}`}>
      <div className="flex items-start gap-3 min-w-0">
        <FileText size={18} className="text-[var(--klein)] mt-0.5 shrink-0" />
        <div className="min-w-0">
          <div className="font-heading font-semibold text-sm">{d.type_label} {d.requirement === "required" && <span className="text-[var(--accent-red)]">*</span>}</div>
          <div className="text-xs text-[var(--tinted-grey-500)] truncate">{uploaded ? d.filename : d.condition_note || "Not uploaded yet"}</div>
          {d.status === "REJECTED" && <div className="text-xs text-[var(--accent-red)]" data-testid={`ap-doc-rejected-${d.type_code}`}>Please re-upload: {d.rejection_reason}</div>}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {uploaded && <span className={`text-[10px] uppercase tracking-widest px-2 py-0.5 ${DOC_TONE[d.status] || ""}`}>{d.status === "PENDING" ? "uploaded" : d.status.toLowerCase()}</span>}
        {canUpload && d.status !== "VERIFIED" && (
          <label className="cursor-pointer" data-testid={`ap-upload-${d.type_code}`}>
            <input type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx" className="hidden" onChange={(e) => onUpload(d.type_code, e.target.files?.[0], e.target)} />
            <span className="inline-flex items-center gap-1 text-xs px-3 py-1.5 border border-[var(--ink)] hover:bg-[var(--ink)] hover:text-white transition-colors"><UploadSimple size={12} />{uploaded ? "Replace" : "Upload"}</span>
          </label>
        )}
      </div>
    </div>
  );
}

function StatusCard({ view, justSubmitted }) {
  const submitted = !["DRAFT", "DOCUMENTS_PENDING"].includes(view.status);
  return (
    <div className={`p-5 border ${submitted ? "border-emerald-600 bg-emerald-50" : "border-amber-300 bg-amber-50"}`} data-testid="ap-status-card">
      <div className="flex items-center gap-2 font-heading font-bold">
        {submitted ? <CheckCircle size={18} className="text-emerald-700" /> : <Warning size={18} className="text-amber-700" />}
        Application {view.application_number} · <span className="uppercase tracking-widest text-xs" data-testid="ap-status">{view.status.replace(/_/g, " ")}</span>
      </div>
      <div className="text-xs mt-1 text-[var(--tinted-grey-500)]">
        {justSubmitted ? "Thank you! Your application was received. Bookmark this page to upload documents. " : ""}
        {view.status === "DOCUMENTS_PENDING" ? "The school asked for corrections or documents. Update and submit again. " : ""}
        This private link expires {new Date(view.expires_at).toLocaleDateString()}.
      </div>
    </div>
  );
}

export default function ApplicantPortalPage() {
  const { token } = useParams();
  const location = useLocation();
  const [view, setView] = useState(null);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState(false);

  const apply = useCallback((data) => {
    setView(data);
    const a = data.application;
    setForm({ ...EMPTY_FORM, ...Object.fromEntries(Object.entries(a).map(([k, v]) => [k, v ?? ""])), form_answers: a.form_answers || {} });
  }, []);
  useEffect(() => {
    api.get(`/public/admissions/t/${token}`).then(({ data }) => apply(data)).catch((e) => setError(formatApiError(e)));
  }, [token, apply]);

  const save = async () => {
    try { setBusy(true); const { data } = await api.put(`/public/admissions/t/${token}`, toPayload(form)); apply(data); toast.success("Saved"); return true; }
    catch (e) { toast.error(formatApiError(e)); return false; } finally { setBusy(false); }
  };
  const submit = async () => {
    if (!(await save())) return;
    try { const { data } = await api.post(`/public/admissions/t/${token}/submit`); apply(data); toast.success("Application submitted"); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const upload = async (code, file, input) => {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { toast.error("File is larger than 10 MB"); input.value = ""; return; }
    try {
      const fd = new FormData(); fd.append("type_code", code); fd.append("file", file);
      const { data } = await api.post(`/public/admissions/t/${token}/documents`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      apply(data); toast.success("Document uploaded");
    } catch (e) { toast.error(formatApiError(e)); } finally { input.value = ""; }
  };

  if (error) return <ApplyShell><div className="text-sm" data-testid="ap-error">{error}</div></ApplyShell>;
  if (!view) return <ApplyShell><div className="text-sm text-[var(--tinted-grey-500)]">Loading…</div></ApplyShell>;
  return (
    <ApplyShell school={view.school}>
      <StatusCard view={view} justSubmitted={location.state?.justSubmitted} />
      <div className="mt-10 bg-white border border-[var(--tinted-grey-200)] p-6" data-testid="ap-documents">
        <div className="overline mb-1">Documents</div>
        <div className="text-xs text-[var(--tinted-grey-500)] mb-3">PDF, JPG, PNG or Word · max 10 MB each. Files are only visible to the school's admission staff.</div>
        {view.documents.map((d) => <DocRow key={d.id} d={d} canUpload={view.can_upload} onUpload={upload} />)}
      </div>
      <div className="mt-10">
        <div className="overline mb-4">Application details</div>
        <ApplicantFormFields form={form} setForm={setForm} config={view} disabled={!view.editable} />
        {view.editable && (
          <div className="mt-8 flex gap-3 flex-wrap">
            <Button variant="outline" onClick={save} disabled={busy} className="rounded-full h-11" data-testid="ap-save">Save draft</Button>
            <Button onClick={submit} disabled={busy} className="rounded-full h-11 bg-[var(--klein)] text-white" data-testid="ap-submit">Submit application</Button>
          </div>
        )}
      </div>
    </ApplyShell>
  );
}
