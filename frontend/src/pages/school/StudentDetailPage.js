import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, User, Users, Plus, Trash, FileText, ClockCounterClockwise, GraduationCap, IdentificationBadge } from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

const tabTrig = "rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold";
const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";
const STATES = ["ACTIVE", "INACTIVE", "ON_LEAVE", "TRANSFERRED", "WITHDRAWN", "GRADUATED", "ALUMNI", "PROSPECT"];
const RELATIONSHIPS = ["father", "mother", "guardian", "legal_guardian", "step_parent", "grandparent", "sibling", "other"];

export default function StudentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [s, setS] = useState(null);
  const [guardians, setGuardians] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [application, setApplication] = useState(null);
  const [appDocs, setAppDocs] = useState([]);
  const [newStatus, setNewStatus] = useState("");
  const [statusReason, setStatusReason] = useState("");
  const [linkOpen, setLinkOpen] = useState(false);
  const [allGuardians, setAllGuardians] = useState([]);
  const [linkForm, setLinkForm] = useState({ guardian_id: "", relationship_type: "guardian", is_primary: false, is_emergency_contact: false });
  const [enrollOpen, setEnrollOpen] = useState(false);
  const [enrollForm, setEnrollForm] = useState({ academic_year: "", class_name: "", section: "", roll_number: "" });

  const load = async () => {
    try {
      const [a, b, c, t] = await Promise.all([
        api.get(`/school/students/${id}`),
        api.get(`/school/students/${id}/guardians`),
        api.get(`/school/students/${id}/enrollments`),
        api.get(`/school/students/${id}/timeline`).catch(() => ({ data: [] })),
      ]);
      setS(a.data); setGuardians(b.data); setEnrollments(c.data); setTimeline(t.data || []);
      if (a.data.application_id) {
        try {
          const [ap, dd] = await Promise.all([
            api.get(`/school/admissions/applications/${a.data.application_id}`),
            api.get(`/school/admissions/applications/${a.data.application_id}/documents`),
          ]);
          setApplication(ap.data); setAppDocs(dd.data);
        } catch { /* no-op */ }
      }
    } catch (e) { toast.error(formatApiError(e)); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const openLink = async () => {
    try {
      const { data } = await api.get("/school/guardians?page_size=200");
      setAllGuardians(data.items || []);
      setLinkOpen(true);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const submitLink = async () => {
    if (!linkForm.guardian_id) return toast.error("Choose a guardian");
    try {
      await api.post(`/school/students/${id}/guardians`, linkForm);
      toast.success("Guardian linked");
      setLinkOpen(false);
      setLinkForm({ guardian_id: "", relationship_type: "guardian", is_primary: false, is_emergency_contact: false });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const unlink = async (rid) => {
    if (!window.confirm("Remove this guardian link?")) return;
    try { await api.delete(`/school/student-guardians/${rid}`); toast.success("Unlinked"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const submitEnrollment = async () => {
    if (!enrollForm.academic_year || !enrollForm.class_name) return toast.error("Year & class are required");
    try {
      const payload = Object.fromEntries(Object.entries(enrollForm).filter(([, v]) => v !== ""));
      await api.post(`/school/students/${id}/enrollments`, payload);
      toast.success("Enrollment recorded");
      setEnrollOpen(false);
      setEnrollForm({ academic_year: "", class_name: "", section: "", roll_number: "" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const changeStatus = async () => {
    if (!newStatus) return;
    try {
      await api.post(`/school/students/${id}/status`, { status: newStatus, reason: statusReason || "Manual update" });
      toast.success("Status updated");
      setNewStatus(""); setStatusReason("");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  if (!s) return <div className="text-[var(--tinted-grey-500)]">Loading…</div>;

  const currentEnrollment = enrollments.find(e => e.enrollment_status === "active") || enrollments[0];
  const linkedGuardianIds = new Set(guardians.map(g => g.guardian_id));
  const primaryGuardian = guardians.find(g => g.is_primary);

  return (
    <div data-testid="student-detail">
      <button onClick={() => navigate("/school/students")} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--tinted-grey-500)] hover:text-[var(--ink)]" data-testid="back-to-students">
        <ArrowLeft size={14} /> All students
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex gap-5 items-start">
          <div className="h-16 w-16 bg-[var(--klein)] text-white flex items-center justify-center font-heading font-black text-2xl">
            {(s.first_name || "?").charAt(0)}{(s.last_name || "").charAt(0)}
          </div>
          <div>
            <div className="overline mb-1 font-mono">{s.admission_number}{s.roll_number ? ` · Roll ${s.roll_number}` : ""}</div>
            <h1 className="font-heading font-black text-4xl tracking-tighter" data-testid="student-name">
              {s.first_name} {s.middle_name || ""} {s.last_name || ""}
            </h1>
            <div className="mt-2 flex items-center gap-2 text-sm text-[var(--tinted-grey-500)]">
              <span>{s.class_name || "—"}</span><span>·</span>
              <span>{s.section ? `Section ${s.section}` : "no section"}</span><span>·</span>
              <span data-testid="student-status" className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${s.status === "ACTIVE" ? "bg-[var(--klein)] text-white" : "bg-[var(--tinted-grey-100)]"}`}>{s.status}</span>
              {s.academic_year ? <><span>·</span><span>{s.academic_year}</span></> : null}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Select value={newStatus} onValueChange={setNewStatus}>
            <SelectTrigger className="rounded-none h-10 w-[180px]" data-testid="student-status-select"><SelectValue placeholder="Change status" /></SelectTrigger>
            <SelectContent>{STATES.map(st => <SelectItem key={st} value={st} data-testid={`status-${st}`}>{st}</SelectItem>)}</SelectContent>
          </Select>
          <Input placeholder="Reason" value={statusReason} onChange={e => setStatusReason(e.target.value)} className="h-10 w-[160px] rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)]" data-testid="status-reason" />
          <Button onClick={changeStatus} disabled={!newStatus} data-testid="student-status-apply" className="rounded-full bg-[var(--ink)] hover:bg-[var(--klein)] text-white transition-colors">Apply</Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-8">
        <Tabs defaultValue="overview">
          <TabsList className="rounded-none bg-transparent h-auto border-b border-[var(--tinted-grey-200)] w-full justify-start p-0 overflow-x-auto">
            <TabsTrigger value="overview" className={tabTrig} data-testid="stab-overview">Overview</TabsTrigger>
            <TabsTrigger value="academic" className={tabTrig} data-testid="stab-academic">Academic</TabsTrigger>
            <TabsTrigger value="guardians" className={tabTrig} data-testid="stab-guardians">Guardians ({guardians.length})</TabsTrigger>
            <TabsTrigger value="documents" className={tabTrig} data-testid="stab-documents">Documents ({appDocs.length})</TabsTrigger>
            <TabsTrigger value="enrollments" className={tabTrig} data-testid="stab-enrollments">Enrollments ({enrollments.length})</TabsTrigger>
            <TabsTrigger value="timeline" className={tabTrig} data-testid="stab-timeline">Timeline</TabsTrigger>
          </TabsList>

          {/* ---- Overview ---- */}
          <TabsContent value="overview" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <Panel title="Identity" testid="panel-identity">
                <Row label="DOB" value={s.date_of_birth} />
                <Row label="Gender" value={s.gender} />
                <Row label="Blood group" value={s.blood_group} />
                <Row label="Nationality" value={s.nationality} />
                <Row label="Mother tongue" value={s.mother_tongue} />
                <Row label="Category" value={s.category} />
              </Panel>
              <Panel title="Primary guardian" testid="panel-primary-guardian">
                {primaryGuardian ? (
                  <div className="text-sm space-y-2">
                    <div className="font-heading font-semibold">{primaryGuardian.guardian?.first_name} {primaryGuardian.guardian?.last_name || ""}</div>
                    <div className="text-[var(--tinted-grey-500)] capitalize">{primaryGuardian.relationship_type}</div>
                    <div className="font-mono text-xs">{primaryGuardian.guardian?.mobile_primary}</div>
                    <div className="font-mono text-xs">{primaryGuardian.guardian?.email || "—"}</div>
                    <Link to={`/school/guardians/${primaryGuardian.guardian_id}`} className="klein-underline text-[var(--klein)] text-xs">View guardian →</Link>
                  </div>
                ) : (
                  <div className="text-sm text-[var(--tinted-grey-500)]">No primary guardian set. <button onClick={openLink} className="klein-underline text-[var(--klein)]">Link one</button></div>
                )}
              </Panel>
              <Panel title="Provenance" testid="panel-provenance">
                <Row label="Source lead" value={s.lead_id ? <Link to={`/school/admissions/inquiries/${s.lead_id}`} className="klein-underline text-[var(--klein)] font-mono text-xs">{s.lead_id.slice(0,8)}…</Link> : "—"} />
                <Row label="Source application" value={s.application_id ? <Link to={`/school/admissions/applications/${s.application_id}`} className="klein-underline text-[var(--klein)] font-mono text-xs">{s.application_id.slice(0,8)}…</Link> : "—"} />
                <Row label="Admission date" value={s.admission_date?.slice(0, 10) || "—"} />
                <Row label="Family" value={s.family_id ? <Link to={`/school/families/${s.family_id}`} className="klein-underline text-[var(--klein)] font-mono text-xs">{s.family_id.slice(0,8)}…</Link> : "—"} />
              </Panel>
              <Panel title="Residential address" testid="panel-address" span2>
                {s.residential_address ? (
                  <div className="text-sm text-[var(--tinted-grey-500)] whitespace-pre-line">
                    {[s.residential_address.line1, s.residential_address.line2, s.residential_address.city, s.residential_address.state, s.residential_address.postal_code, s.residential_address.country].filter(Boolean).join("\n") || "—"}
                  </div>
                ) : <div className="text-sm text-[var(--tinted-grey-500)]">No address on file.</div>}
              </Panel>
              <Panel title="Missing info" testid="panel-missing" tone="warn">
                <ul className="text-sm space-y-1">
                  {!s.date_of_birth && <li className="text-[var(--accent-red)]">• Missing date of birth</li>}
                  {guardians.length === 0 && <li className="text-[var(--accent-red)]">• No guardians linked</li>}
                  {!s.residential_address && <li className="text-[var(--accent-red)]">• No residential address</li>}
                  {!s.blood_group && <li className="text-[var(--tinted-grey-500)]">• No blood group</li>}
                  {s.date_of_birth && guardians.length > 0 && s.residential_address && s.blood_group && (
                    <li className="text-[var(--klein)]">✓ Record is complete</li>
                  )}
                </ul>
              </Panel>
            </div>
          </TabsContent>

          {/* ---- Academic ---- */}
          <TabsContent value="academic" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Panel title="Current placement" testid="panel-academic-current">
                <Row label="Academic year" value={s.academic_year} />
                <Row label="Class" value={s.class_name} />
                <Row label="Section" value={s.section} />
                <Row label="Roll #" value={s.roll_number} />
                <Row label="House" value={s.house} />
                <Row label="Student code" value={s.student_code} />
              </Panel>
              <Panel title="Active enrollment" testid="panel-active-enrollment">
                {currentEnrollment ? (
                  <div className="text-sm space-y-2">
                    <div className="font-heading font-semibold">{currentEnrollment.academic_year} · {currentEnrollment.class_name}{currentEnrollment.section ? ` · ${currentEnrollment.section}` : ""}</div>
                    <Row label="Status" value={currentEnrollment.enrollment_status} />
                    <Row label="Roll" value={currentEnrollment.roll_number} />
                    <Row label="Started" value={currentEnrollment.start_date?.slice(0, 10)} />
                    {currentEnrollment.end_date && <Row label="Ended" value={currentEnrollment.end_date.slice(0, 10)} />}
                  </div>
                ) : (
                  <div className="text-sm text-[var(--tinted-grey-500)]">No active enrollment on record.</div>
                )}
              </Panel>
            </div>
          </TabsContent>

          {/* ---- Guardians ---- */}
          <TabsContent value="guardians" className="mt-6">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm text-[var(--tinted-grey-500)]">{guardians.length} linked guardian{guardians.length === 1 ? "" : "s"}</div>
              <Button onClick={openLink} data-testid="btn-link-guardian" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> Link guardian</Button>
            </div>
            <div className="bg-white border border-[var(--tinted-grey-200)] divide-y divide-[var(--tinted-grey-200)]" data-testid="student-guardians-list">
              {guardians.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]">No guardians linked yet.</div>}
              {guardians.map(r => (
                <div key={r.id} className="p-4 flex items-center justify-between" data-testid={`sg-${r.id}`}>
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 bg-[var(--tinted-grey-100)] rounded-full flex items-center justify-center">
                      <User size={18} weight="duotone" className="text-[var(--klein)]" />
                    </div>
                    <div>
                      <Link to={`/school/guardians/${r.guardian_id}`} className="font-heading font-semibold klein-underline">{r.guardian?.first_name} {r.guardian?.last_name || ""}</Link>
                      <div className="text-xs text-[var(--tinted-grey-500)] capitalize">{r.relationship_type} · {r.guardian?.mobile_primary}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {r.is_primary && <span className="text-[10px] uppercase tracking-widest bg-[var(--klein)] text-white px-1.5 py-0.5">primary</span>}
                    {r.is_emergency_contact && <span className="text-[10px] uppercase tracking-widest bg-[var(--accent-red)] text-white px-1.5 py-0.5">emergency</span>}
                    <button onClick={() => unlink(r.id)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)]" data-testid={`unlink-${r.id}`}><Trash size={16} /></button>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* ---- Documents ---- */}
          <TabsContent value="documents" className="mt-6">
            {application ? (
              <>
                <div className="text-sm text-[var(--tinted-grey-500)] mb-4">
                  Documents inherited from admission application <Link to={`/school/admissions/applications/${s.application_id}`} className="klein-underline text-[var(--klein)] font-mono text-xs">{application.application_number}</Link>
                </div>
                <div className="bg-white border border-[var(--tinted-grey-200)] divide-y divide-[var(--tinted-grey-200)]" data-testid="student-docs-list">
                  {appDocs.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]">No documents on file.</div>}
                  {appDocs.map(d => (
                    <div key={d.id} className="p-4 flex items-center justify-between" data-testid={`doc-${d.id}`}>
                      <div className="flex items-center gap-3">
                        <FileText size={18} weight="duotone" className="text-[var(--klein)]" />
                        <div>
                          <div className="font-heading font-semibold text-sm">{d.doc_type}</div>
                          <div className="text-xs text-[var(--tinted-grey-500)]">{d.filename}</div>
                        </div>
                      </div>
                      <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${d.status === "verified" ? "bg-[var(--klein)] text-white" : d.status === "rejected" ? "bg-[var(--accent-red)] text-white" : "bg-[var(--tinted-grey-100)]"}`}>{d.status}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-sm text-[var(--tinted-grey-500)]" data-testid="documents-empty">
                No admission application linked. Student documents will land here once uploaded (fees / academic modules can extend this later).
              </div>
            )}
          </TabsContent>

          {/* ---- Enrollments ---- */}
          <TabsContent value="enrollments" className="mt-6">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm text-[var(--tinted-grey-500)]">{enrollments.length} enrollment record{enrollments.length === 1 ? "" : "s"}</div>
              <Dialog open={enrollOpen} onOpenChange={setEnrollOpen}>
                <DialogTrigger asChild>
                  <Button data-testid="btn-new-enrollment" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> New enrollment</Button>
                </DialogTrigger>
                <DialogContent className="rounded-none max-w-md">
                  <DialogHeader><DialogTitle>New enrollment</DialogTitle></DialogHeader>
                  <div className="grid grid-cols-2 gap-4">
                    <div><Label className="overline">Academic year</Label><Input value={enrollForm.academic_year} onChange={e => setEnrollForm({ ...enrollForm, academic_year: e.target.value })} className={field} data-testid="en-year" /></div>
                    <div><Label className="overline">Class</Label><Input value={enrollForm.class_name} onChange={e => setEnrollForm({ ...enrollForm, class_name: e.target.value })} className={field} data-testid="en-class" /></div>
                    <div><Label className="overline">Section</Label><Input value={enrollForm.section} onChange={e => setEnrollForm({ ...enrollForm, section: e.target.value })} className={field} data-testid="en-section" /></div>
                    <div><Label className="overline">Roll</Label><Input value={enrollForm.roll_number} onChange={e => setEnrollForm({ ...enrollForm, roll_number: e.target.value })} className={field} data-testid="en-roll" /></div>
                  </div>
                  <DialogFooter><Button onClick={submitEnrollment} data-testid="en-submit" className="rounded-none bg-[var(--klein)] text-white">Record</Button></DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
            <div className="bg-white border border-[var(--tinted-grey-200)] divide-y divide-[var(--tinted-grey-200)]" data-testid="student-enrollments-list">
              {enrollments.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]">No enrollment history.</div>}
              {enrollments.map(e => (
                <div key={e.id} className="p-4 flex items-start justify-between" data-testid={`enroll-${e.id}`}>
                  <div className="flex items-start gap-3">
                    <GraduationCap size={18} weight="duotone" className="text-[var(--klein)] mt-1" />
                    <div>
                      <div className="font-heading font-semibold">{e.academic_year} · {e.class_name}{e.section ? ` · Section ${e.section}` : ""}</div>
                      <div className="text-xs text-[var(--tinted-grey-500)] mt-1">
                        {e.roll_number ? `Roll ${e.roll_number} · ` : ""}
                        {e.start_date ? `Started ${e.start_date.slice(0, 10)}` : ""}
                        {e.end_date ? ` · Ended ${e.end_date.slice(0, 10)}` : ""}
                      </div>
                    </div>
                  </div>
                  <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${e.enrollment_status === "active" ? "bg-[var(--klein)] text-white" : "bg-[var(--tinted-grey-100)]"}`}>{e.enrollment_status}</span>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* ---- Timeline ---- */}
          <TabsContent value="timeline" className="mt-6">
            <div className="bg-white border border-[var(--tinted-grey-200)] divide-y divide-[var(--tinted-grey-200)]" data-testid="student-timeline-list">
              {timeline.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]">No activity yet.</div>}
              {timeline.map(t => (
                <div key={t.id} className="p-4 flex items-start gap-3" data-testid={`event-${t.id}`}>
                  <div className="h-8 w-8 rounded-full bg-[var(--tinted-grey-100)] flex items-center justify-center shrink-0">
                    <ClockCounterClockwise size={14} weight="duotone" className="text-[var(--klein)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-heading font-semibold text-sm">{t.action}</div>
                    <div className="text-xs text-[var(--tinted-grey-500)] mt-0.5">
                      by {t.actor_email || "system"} · {new Date(t.created_at).toLocaleString()}
                    </div>
                    {t.metadata && Object.keys(t.metadata).length > 0 && (
                      <div className="text-[11px] text-[var(--tinted-grey-500)] font-mono mt-1 break-words">
                        {JSON.stringify(t.metadata).slice(0, 200)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Link guardian dialog */}
      <Dialog open={linkOpen} onOpenChange={setLinkOpen}>
        <DialogContent className="rounded-none max-w-md">
          <DialogHeader><DialogTitle>Link a guardian</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div>
              <Label className="overline">Guardian</Label>
              <Select value={linkForm.guardian_id} onValueChange={(v) => setLinkForm({ ...linkForm, guardian_id: v })}>
                <SelectTrigger className="rounded-none h-10 mt-2" data-testid="link-guardian-select"><SelectValue placeholder="Choose guardian" /></SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  {allGuardians.filter(g => !linkedGuardianIds.has(g.id)).map(g => (
                    <SelectItem key={g.id} value={g.id} data-testid={`lg-${g.id}`}>
                      {g.first_name} {g.last_name || ""} · {g.mobile_primary}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="overline">Relationship</Label>
              <Select value={linkForm.relationship_type} onValueChange={(v) => setLinkForm({ ...linkForm, relationship_type: v })}>
                <SelectTrigger className="rounded-none h-10 mt-2" data-testid="link-rel-select"><SelectValue /></SelectTrigger>
                <SelectContent>{RELATIONSHIPS.map(r => <SelectItem key={r} value={r} data-testid={`lr-${r}`}>{r}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={linkForm.is_primary} onChange={e => setLinkForm({ ...linkForm, is_primary: e.target.checked })} data-testid="link-is-primary" />
              Set as primary contact
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={linkForm.is_emergency_contact} onChange={e => setLinkForm({ ...linkForm, is_emergency_contact: e.target.checked })} data-testid="link-is-emergency" />
              Emergency contact
            </label>
          </div>
          <DialogFooter><Button onClick={submitLink} data-testid="link-submit" className="rounded-none bg-[var(--klein)] text-white">Link</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Panel({ title, testid, children, span2, tone }) {
  return (
    <div className={`bg-white border ${tone === "warn" ? "border-[var(--accent-red)]/30" : "border-[var(--tinted-grey-200)]"} p-5 ${span2 ? "lg:col-span-2" : ""}`} data-testid={testid}>
      <div className="overline mb-3">{title}</div>
      {children}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="grid grid-cols-2 py-1 text-sm border-b border-[var(--tinted-grey-100)] last:border-0">
      <dt className="overline text-[10px] self-center">{label}</dt>
      <dd>{value ?? "—"}</dd>
    </div>
  );
}
