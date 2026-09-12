import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, IdentificationBadge, FileText, GraduationCap, AirplaneTilt, ClockCounterClockwise, Trash, Plus } from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useStaffMeta, EMPLOYMENT_STATUSES, STATUS_TONE } from "./_shared";

const tabTrig = "rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold";
const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function StaffDetailPage() {
  const { id } = useParams(); const navigate = useNavigate();
  const meta = useStaffMeta();
  const [emp, setEmp] = useState(null);
  const [docs, setDocs] = useState([]);
  const [quals, setQuals] = useState([]);
  const [leaves, setLeaves] = useState([]);
  const [balances, setBalances] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [newStatus, setNewStatus] = useState("");
  const [reason, setReason] = useState("");
  const [docOpen, setDocOpen] = useState(false);
  const [docForm, setDocForm] = useState({ doc_type: "", filename: "", storage_key: "" });
  const [qualOpen, setQualOpen] = useState(false);
  const [qualForm, setQualForm] = useState({ kind: "degree", degree_name: "", institution: "", year_of_completion: "", subject_id: "" });

  const load = async () => {
    try {
      const [e, d, q, l, b, s] = await Promise.all([
        api.get(`/school/staff/employees/${id}`),
        api.get(`/school/staff/employees/${id}/documents`),
        api.get(`/school/staff/employees/${id}/qualifications`),
        api.get(`/school/staff/leave-applications?employee_id=${id}&page_size=50`),
        api.get(`/school/staff/leave-balances?employee_id=${id}`),
        api.get(`/school/academic/subjects`).catch(() => ({ data: [] })),
      ]);
      setEmp(e.data); setDocs(d.data); setQuals(q.data); setLeaves(l.data.items || []); setBalances(b.data); setSubjects(s.data);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const changeStatus = async () => {
    if (!newStatus) return;
    try { await api.post(`/school/staff/employees/${id}/status`, { status: newStatus, reason }); toast.success("Status updated"); setNewStatus(""); setReason(""); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const addDoc = async () => {
    if (!docForm.doc_type || !docForm.filename) return toast.error("Type & filename required");
    try {
      await api.post(`/school/staff/employees/${id}/documents`, { ...docForm, storage_key: docForm.storage_key || `local/${Date.now()}-${docForm.filename}` });
      toast.success("Document added"); setDocOpen(false);
      setDocForm({ doc_type: "", filename: "", storage_key: "" }); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const delDoc = async (did) => {
    if (!window.confirm("Delete this document record?")) return;
    try { await api.delete(`/school/staff/documents/${did}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const addQual = async () => {
    try {
      const payload = { ...qualForm };
      Object.keys(payload).forEach(k => payload[k] === "" && delete payload[k]);
      await api.post(`/school/staff/employees/${id}/qualifications`, payload);
      toast.success("Qualification added"); setQualOpen(false);
      setQualForm({ kind: "degree", degree_name: "", institution: "", year_of_completion: "", subject_id: "" }); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const delQual = async (qid) => {
    try { await api.delete(`/school/staff/qualifications/${qid}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  if (!emp) return <div className="text-[var(--tinted-grey-500)]">Loading…</div>;
  const dept = meta.departments.find(d => d.id === emp.department_id);
  const desig = meta.designations.find(d => d.id === emp.designation_id);

  return (
    <div data-testid="staff-detail">
      <button onClick={() => navigate("/school/staff")} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--tinted-grey-500)] hover:text-[var(--ink)]" data-testid="back-to-staff"><ArrowLeft size={14} /> All staff</button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex gap-5 items-start">
          <div className="h-16 w-16 bg-[var(--klein)] text-white flex items-center justify-center font-heading font-black text-2xl">
            {(emp.first_name || "?").charAt(0)}{(emp.last_name || "").charAt(0)}
          </div>
          <div>
            <div className="overline mb-1 font-mono">{emp.employee_code}</div>
            <h1 className="font-heading font-black text-4xl tracking-tighter" data-testid="staff-name">{emp.first_name} {emp.middle_name || ""} {emp.last_name || ""}</h1>
            <div className="mt-2 flex items-center gap-2 text-sm text-[var(--tinted-grey-500)]">
              <span>{desig?.title || "—"}</span><span>·</span>
              <span>{dept?.name || "—"}</span><span>·</span>
              <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${STATUS_TONE[emp.status] || ""}`} data-testid="staff-status">{(emp.status || "").replace("_", " ")}</span>
              <span>·</span><span className="capitalize">{(emp.employment_type || "").replace("_", " ")}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Select value={newStatus} onValueChange={setNewStatus}>
            <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="staff-status-select"><SelectValue placeholder="Change status" /></SelectTrigger>
            <SelectContent>{EMPLOYMENT_STATUSES.map(s => <SelectItem key={s} value={s}>{s.replace("_", " ")}</SelectItem>)}</SelectContent>
          </Select>
          <Input placeholder="Reason" value={reason} onChange={e => setReason(e.target.value)} className="h-10 w-[160px] rounded-none" data-testid="staff-status-reason" />
          <Button onClick={changeStatus} disabled={!newStatus} data-testid="staff-status-apply" className="rounded-full bg-[var(--ink)] hover:bg-[var(--klein)] text-white">Apply</Button>
        </div>
      </div>

      <div className="mt-8">
        <Tabs defaultValue="overview">
          <TabsList className="rounded-none bg-transparent h-auto border-b border-[var(--tinted-grey-200)] w-full justify-start p-0 overflow-x-auto">
            <TabsTrigger value="overview" className={tabTrig} data-testid="stab-overview">Overview</TabsTrigger>
            <TabsTrigger value="qualifications" className={tabTrig} data-testid="stab-quals">Qualifications ({quals.length})</TabsTrigger>
            <TabsTrigger value="documents" className={tabTrig} data-testid="stab-docs">Documents ({docs.length})</TabsTrigger>
            <TabsTrigger value="leave" className={tabTrig} data-testid="stab-leave">Leave ({leaves.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Panel title="Identity" testid="p-identity">
                <Row label="DOB" value={emp.date_of_birth} />
                <Row label="Gender" value={emp.gender} />
                <Row label="Blood group" value={emp.blood_group} />
                <Row label="Nationality" value={emp.nationality} />
              </Panel>
              <Panel title="Contact" testid="p-contact">
                <Row label="Mobile" value={<span className="font-mono">{emp.mobile_primary || "—"}</span>} />
                <Row label="Alt mobile" value={<span className="font-mono">{emp.mobile_secondary || "—"}</span>} />
                <Row label="Email" value={<span className="font-mono text-xs">{emp.email_personal || "—"}</span>} />
              </Panel>
              <Panel title="Employment" testid="p-employment">
                <Row label="Joining" value={emp.joining_date} />
                <Row label="Probation end" value={emp.probation_end_date} />
                <Row label="Confirmation" value={emp.confirmation_date} />
                {emp.exit_date && <Row label="Exit" value={emp.exit_date} />}
                {emp.exit_reason && <Row label="Exit reason" value={emp.exit_reason} />}
              </Panel>
              <Panel title="Attendance hooks (Prompt 6)" testid="p-attendance">
                <Row label="Biometric ID" value={<span className="font-mono">{emp.biometric_id || "—"}</span>} />
                <Row label="Attendance #" value={<span className="font-mono">{emp.attendance_number || "—"}</span>} />
              </Panel>
            </div>
          </TabsContent>

          <TabsContent value="qualifications" className="mt-6">
            <div className="flex justify-between items-center mb-4">
              <div className="text-sm text-[var(--tinted-grey-500)]">{quals.length} record{quals.length === 1 ? "" : "s"}</div>
              <Dialog open={qualOpen} onOpenChange={setQualOpen}>
                <DialogTrigger asChild><Button data-testid="btn-add-qual" className="rounded-full bg-[var(--klein)] text-white"><Plus size={12} className="mr-1"/> Add</Button></DialogTrigger>
                <DialogContent className="rounded-none max-w-md">
                  <DialogHeader><DialogTitle>New qualification</DialogTitle></DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label className="overline">Kind</Label>
                      <Select value={qualForm.kind} onValueChange={v => setQualForm({ ...qualForm, kind: v })}>
                        <SelectTrigger className="rounded-none h-10 mt-2" data-testid="qual-kind"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="degree">Degree</SelectItem>
                          <SelectItem value="certification">Certification</SelectItem>
                          <SelectItem value="subject">Subject eligibility</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    {qualForm.kind !== "subject" ? (
                      <>
                        <div><Label className="overline">Name</Label><Input value={qualForm.degree_name} onChange={e => setQualForm({ ...qualForm, degree_name: e.target.value })} className={field} data-testid="qual-name" /></div>
                        <div><Label className="overline">Institution</Label><Input value={qualForm.institution} onChange={e => setQualForm({ ...qualForm, institution: e.target.value })} className={field} data-testid="qual-inst" /></div>
                        <div><Label className="overline">Year</Label><Input value={qualForm.year_of_completion} onChange={e => setQualForm({ ...qualForm, year_of_completion: e.target.value })} className={field} data-testid="qual-year" /></div>
                      </>
                    ) : (
                      <div>
                        <Label className="overline">Subject</Label>
                        <Select value={qualForm.subject_id} onValueChange={v => setQualForm({ ...qualForm, subject_id: v })}>
                          <SelectTrigger className="rounded-none h-10 mt-2" data-testid="qual-subject"><SelectValue placeholder="Pick subject" /></SelectTrigger>
                          <SelectContent>{subjects.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                  <DialogFooter><Button onClick={addQual} data-testid="qual-submit" className="rounded-none bg-[var(--klein)] text-white">Add</Button></DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
            <div className="bg-white border border-[var(--tinted-grey-200)] divide-y divide-[var(--tinted-grey-200)]" data-testid="quals-list">
              {quals.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]">No qualifications yet.</div>}
              {quals.map(q => (
                <div key={q.id} className="p-4 flex items-start justify-between" data-testid={`qual-${q.id}`}>
                  <div className="flex items-start gap-3">
                    <GraduationCap size={18} weight="duotone" className="text-[var(--klein)] mt-1"/>
                    <div>
                      <div className="font-heading font-semibold text-sm">
                        {q.kind === "subject" ? subjects.find(s => s.id === q.subject_id)?.name || "Subject" : q.degree_name || q.kind}
                      </div>
                      <div className="text-xs text-[var(--tinted-grey-500)]">
                        {[q.institution, q.year_of_completion, q.grade].filter(Boolean).join(" · ") || "—"}
                      </div>
                    </div>
                  </div>
                  <button onClick={() => delQual(q.id)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)]" data-testid={`qual-del-${q.id}`}><Trash size={14}/></button>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="documents" className="mt-6">
            <div className="flex justify-between items-center mb-4">
              <div className="text-sm text-[var(--tinted-grey-500)]">{docs.length} document{docs.length === 1 ? "" : "s"}</div>
              <Dialog open={docOpen} onOpenChange={setDocOpen}>
                <DialogTrigger asChild><Button data-testid="btn-add-doc" className="rounded-full bg-[var(--klein)] text-white"><Plus size={12} className="mr-1"/> Add</Button></DialogTrigger>
                <DialogContent className="rounded-none max-w-md">
                  <DialogHeader><DialogTitle>New document</DialogTitle></DialogHeader>
                  <div className="space-y-4">
                    <div><Label className="overline">Type</Label><Input placeholder="aadhaar / pan / resume" value={docForm.doc_type} onChange={e => setDocForm({ ...docForm, doc_type: e.target.value })} className={field} data-testid="doc-type" /></div>
                    <div><Label className="overline">Filename</Label><Input value={docForm.filename} onChange={e => setDocForm({ ...docForm, filename: e.target.value })} className={field} data-testid="doc-filename" /></div>
                    <div><Label className="overline">Storage key (optional)</Label><Input placeholder="Auto-generated if blank" value={docForm.storage_key} onChange={e => setDocForm({ ...docForm, storage_key: e.target.value })} className={field} data-testid="doc-key" /></div>
                  </div>
                  <DialogFooter><Button onClick={addDoc} data-testid="doc-submit" className="rounded-none bg-[var(--klein)] text-white">Add</Button></DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
            <div className="bg-white border border-[var(--tinted-grey-200)] divide-y divide-[var(--tinted-grey-200)]" data-testid="docs-list">
              {docs.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]">No documents yet.</div>}
              {docs.map(d => (
                <div key={d.id} className="p-4 flex items-start justify-between" data-testid={`doc-${d.id}`}>
                  <div className="flex items-start gap-3">
                    <FileText size={18} weight="duotone" className="text-[var(--klein)]" />
                    <div>
                      <div className="font-heading font-semibold text-sm">{d.doc_type}</div>
                      <div className="text-xs text-[var(--tinted-grey-500)]">{d.filename}</div>
                    </div>
                  </div>
                  <button onClick={() => delDoc(d.id)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)]" data-testid={`doc-del-${d.id}`}><Trash size={14}/></button>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="leave" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Panel title="Balances" testid="p-balances">
                {balances.length === 0 && <div className="text-sm text-[var(--tinted-grey-500)]">No balances yet — apply for leave to seed a balance.</div>}
                {balances.map(b => {
                  const lt = meta.leaveTypes.find(x => x.id === b.leave_type_id);
                  return (
                    <div key={b.id} className="flex items-center justify-between py-1 text-sm border-b border-[var(--tinted-grey-100)] last:border-0" data-testid={`bal-${b.id}`}>
                      <div><span className="font-mono text-xs">{lt?.code || "?"}</span> · <span className="text-[var(--tinted-grey-500)]">{b.year}</span></div>
                      <div className="font-mono text-xs">{b.balance}/{b.allocated}</div>
                    </div>
                  );
                })}
              </Panel>
              <Panel title="Applications" testid="p-leaves">
                {leaves.length === 0 && <div className="text-sm text-[var(--tinted-grey-500)]">No applications yet.</div>}
                {leaves.map(l => {
                  const lt = meta.leaveTypes.find(x => x.id === l.leave_type_id);
                  return (
                    <div key={l.id} className="flex items-start gap-3 py-2 border-b border-[var(--tinted-grey-100)] last:border-0" data-testid={`leave-${l.id}`}>
                      <AirplaneTilt size={16} weight="duotone" className="text-[var(--klein)] mt-0.5"/>
                      <div className="flex-1">
                        <div className="text-sm font-heading font-semibold">{lt?.name || "?"} · {l.days}d</div>
                        <div className="text-xs text-[var(--tinted-grey-500)]">{l.start_date?.slice(0, 10)} → {l.end_date?.slice(0, 10)}</div>
                      </div>
                      <span className="text-[10px] uppercase tracking-widest">{l.status}</span>
                    </div>
                  );
                })}
              </Panel>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function Panel({ title, testid, children }) {
  return <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid={testid}><div className="overline mb-3">{title}</div>{children}</div>;
}
function Row({ label, value }) {
  return <div className="grid grid-cols-2 py-1 text-sm border-b border-[var(--tinted-grey-100)] last:border-0"><dt className="overline text-[10px] self-center">{label}</dt><dd>{value ?? "—"}</dd></div>;
}
