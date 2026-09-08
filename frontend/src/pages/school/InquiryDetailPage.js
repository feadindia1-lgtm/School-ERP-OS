import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, PhoneCall, Calendar as CalendarIcon, ClipboardText, Plus, CheckCircle,
} from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const tabTrig = "rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold";
const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function InquiryDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [lead, setLead] = useState(null);
  const [activities, setActivities] = useState([]);
  const [followups, setFollowups] = useState([]);
  const [settings, setSettings] = useState(null);
  const [act, setAct] = useState({ activity_type: "phone_call", subject: "", outcome: "", notes: "", next_followup_at: "" });
  const [fu, setFu] = useState({ title: "Follow-up", due_at: "", channel: "phone_call", notes: "" });

  const load = async () => {
    try {
      const [l, a, f, s] = await Promise.all([
        api.get(`/school/crm/leads/${id}`),
        api.get(`/school/crm/leads/${id}/activities`),
        api.get(`/school/crm/followups?lead_id=${id}`),
        api.get(`/school/crm/settings`),
      ]);
      setLead(l.data); setActivities(a.data); setFollowups(f.data); setSettings(s.data);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const moveStage = async (stage) => {
    try { await api.post(`/school/crm/leads/${id}/stage`, { stage }); toast.success(`Stage → ${stage}`); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const addActivity = async () => {
    try { await api.post(`/school/crm/leads/${id}/activities`, act); toast.success("Activity added"); setAct({ ...act, subject:"", notes:"", outcome:"" }); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const addFollowup = async () => {
    if (!fu.due_at) return toast.error("Due date required");
    try { await api.post(`/school/crm/leads/${id}/followups`, fu); toast.success("Follow-up scheduled"); setFu({ ...fu, notes:"" }); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const completeFu = async (fuid) => {
    try { await api.patch(`/school/crm/followups/${fuid}`, { status: "completed" }); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const createApplication = async () => {
    try {
      const { data } = await api.post(`/school/admissions/applications`, {
        lead_id: id, academic_year: lead.academic_year || "AY 2026-27",
        class_requested: lead.class_seeking || "Grade 1",
        student_first_name: lead.student_first_name, student_last_name: lead.student_last_name,
        student_dob: lead.student_dob, student_gender: lead.student_gender,
        parent_name: lead.parent_name, parent_relationship: lead.parent_relationship,
        parent_mobile: lead.parent_mobile, parent_email: lead.parent_email,
      });
      toast.success("Application created");
      navigate(`/school/admissions/applications/${data.id}`);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  if (!lead) return <div className="text-[var(--tinted-grey-500)]">Loading…</div>;

  const stages = settings?.pipeline_stages || [];

  return (
    <div data-testid="inquiry-detail">
      <button onClick={() => navigate("/school/admissions/inquiries")} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--tinted-grey-500)] hover:text-[var(--ink)]" data-testid="back-to-inquiries">
        <ArrowLeft size={14} /> All inquiries
      </button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="overline mb-2 font-mono">{lead.inquiry_number}</div>
          <h1 className="font-heading font-black text-4xl tracking-tighter" data-testid="detail-student-name">
            {lead.student_first_name} {lead.student_last_name}
          </h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">
            {lead.class_seeking || "—"} · {lead.academic_year || "—"} · Source: {lead.source} · Priority: {lead.priority}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Select value={lead.stage} onValueChange={moveStage}>
            <SelectTrigger className="rounded-none h-10 w-[220px]" data-testid="detail-stage-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              {stages.map(s => <SelectItem key={s.code} value={s.code} data-testid={`detail-stage-${s.code}`}>{s.label}</SelectItem>)}
            </SelectContent>
          </Select>
          {lead.application_id ? (
            <Button data-testid="detail-open-app" onClick={() => navigate(`/school/admissions/applications/${lead.application_id}`)} className="rounded-full">Open application</Button>
          ) : (
            <Button data-testid="detail-create-app" onClick={createApplication} className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><ClipboardText size={14} className="mr-1" /> Create application</Button>
          )}
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-white border border-[var(--tinted-grey-200)] p-5">
            <div className="overline mb-3">Parent / Guardian</div>
            <div className="font-heading font-bold">{lead.parent_name}</div>
            <div className="text-sm text-[var(--tinted-grey-500)] capitalize">{lead.parent_relationship}</div>
            <div className="mt-3 space-y-1 text-sm font-mono">
              <div>{lead.parent_mobile}</div>
              {lead.parent_email && <div>{lead.parent_email}</div>}
              {lead.alt_contact && <div>Alt · {lead.alt_contact}</div>}
            </div>
          </div>
          {lead.notes && <div className="bg-white border border-[var(--tinted-grey-200)] p-5"><div className="overline mb-2">Notes</div><div className="text-sm">{lead.notes}</div></div>}
        </div>

        <div className="lg:col-span-8">
          <Tabs defaultValue="timeline">
            <TabsList className="rounded-none bg-transparent h-auto border-b border-[var(--tinted-grey-200)] w-full justify-start p-0">
              <TabsTrigger value="timeline" className={tabTrig} data-testid="tab-timeline">Timeline</TabsTrigger>
              <TabsTrigger value="followups" className={tabTrig} data-testid="tab-followups">Follow-ups</TabsTrigger>
            </TabsList>

            <TabsContent value="timeline" className="mt-4 space-y-4">
              <div className="bg-white border border-[var(--tinted-grey-200)] p-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <Label className="overline">Activity type</Label>
                    <Select value={act.activity_type} onValueChange={(v)=>setAct({...act, activity_type:v})}>
                      <SelectTrigger className="mt-2 rounded-none h-10 border-x-0 border-t-0 border-b-2 border-[var(--ink)]" data-testid="act-type"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {["phone_call","whatsapp","sms","email","meeting","note","task","other"].map(t=><SelectItem key={t} value={t} data-testid={`act-type-${t}`}>{t.replace(/_/g," ")}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div><Label className="overline">Subject</Label><Input value={act.subject} onChange={e=>setAct({...act, subject:e.target.value})} className={field} data-testid="act-subject" /></div>
                  <div className="md:col-span-2"><Label className="overline">Notes</Label><Textarea rows={2} value={act.notes} onChange={e=>setAct({...act, notes:e.target.value})} className="mt-2 rounded-none focus-visible:ring-0 focus-visible:border-[var(--klein)]" data-testid="act-notes" /></div>
                  <div><Label className="overline">Next follow-up</Label><Input type="datetime-local" value={act.next_followup_at} onChange={e=>setAct({...act, next_followup_at:e.target.value ? new Date(e.target.value).toISOString() : ""})} className={field} data-testid="act-next" /></div>
                  <div className="flex items-end"><Button onClick={addActivity} data-testid="act-submit" className="rounded-full bg-[var(--ink)] hover:bg-[var(--klein)] text-white transition-colors"><Plus size={14} className="mr-1" /> Log activity</Button></div>
                </div>
              </div>

              <div className="bg-white border border-[var(--tinted-grey-200)]" data-testid="timeline-list">
                {activities.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]">No activities yet.</div>}
                {activities.map(a => (
                  <div key={a.id} className="p-4 border-b border-[var(--tinted-grey-200)] last:border-b-0">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="uppercase tracking-widest text-[var(--klein)]">{a.activity_type.replace(/_/g," ")}</span>
                      <span className="font-mono text-[10px] text-[var(--tinted-grey-400)]">{a.created_at?.slice(0,19).replace("T"," ")}</span>
                    </div>
                    {a.subject && <div className="font-heading font-semibold">{a.subject}</div>}
                    {a.notes && <div className="text-sm text-[var(--tinted-grey-500)] mt-1">{a.notes}</div>}
                  </div>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="followups" className="mt-4 space-y-4">
              <div className="bg-white border border-[var(--tinted-grey-200)] p-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div><Label className="overline">Title</Label><Input value={fu.title} onChange={e=>setFu({...fu, title:e.target.value})} className={field} data-testid="fu-title" /></div>
                  <div><Label className="overline">Due</Label><Input type="datetime-local" value={fu.due_at?.slice(0,16)} onChange={e=>setFu({...fu, due_at:e.target.value ? new Date(e.target.value).toISOString() : ""})} className={field} data-testid="fu-due" /></div>
                  <div className="md:col-span-2 flex justify-end"><Button onClick={addFollowup} data-testid="fu-submit" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><CalendarIcon size={14} className="mr-1" /> Schedule</Button></div>
                </div>
              </div>
              <div className="bg-white border border-[var(--tinted-grey-200)]" data-testid="followups-list">
                {followups.length === 0 && <div className="p-6 text-sm text-[var(--tinted-grey-500)]">No follow-ups.</div>}
                {followups.map(f => (
                  <div key={f.id} className="p-4 border-b border-[var(--tinted-grey-200)] last:border-b-0 flex items-center justify-between" data-testid={`fu-row-${f.id}`}>
                    <div>
                      <div className="font-heading font-semibold">{f.title}</div>
                      <div className="text-xs text-[var(--tinted-grey-500)]">{f.due_at?.slice(0,16).replace("T"," ")} · {f.channel.replace(/_/g," ")} · {f.status}</div>
                    </div>
                    {f.status === "pending" && <Button size="sm" variant="outline" onClick={() => completeFu(f.id)} data-testid={`fu-complete-${f.id}`}><CheckCircle size={12} className="mr-1" /> Complete</Button>}
                  </div>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
