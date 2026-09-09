import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, User, GraduationCap, Pencil, FloppyDisk } from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";
const RELATIONSHIPS = ["father", "mother", "guardian", "legal_guardian", "step_parent", "grandparent", "sibling", "other"];

export default function GuardianDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [g, setG] = useState(null);
  const [students, setStudents] = useState([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  const load = async () => {
    try {
      const [a, b] = await Promise.all([
        api.get(`/school/guardians/${id}`),
        api.get(`/school/guardians/${id}/students`).catch(() => ({ data: [] })),
      ]);
      setG(a.data); setStudents(b.data || []);
      setForm({
        first_name: a.data.first_name || "", last_name: a.data.last_name || "",
        relationship_type: a.data.relationship_type || "guardian",
        mobile_primary: a.data.mobile_primary || "", mobile_secondary: a.data.mobile_secondary || "",
        email: a.data.email || "", occupation: a.data.occupation || "", employer: a.data.employer || "",
      });
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const save = async () => {
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ""));
      await api.patch(`/school/guardians/${id}`, payload);
      toast.success("Guardian updated"); setEditing(false); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  if (!g) return <div className="text-[var(--tinted-grey-500)]">Loading…</div>;

  return (
    <div data-testid="guardian-detail">
      <button onClick={() => navigate("/school/guardians")} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--tinted-grey-500)] hover:text-[var(--ink)]" data-testid="back-to-guardians">
        <ArrowLeft size={14} /> All guardians
      </button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-5">
          <div className="h-16 w-16 bg-[var(--klein)] text-white flex items-center justify-center font-heading font-black text-2xl">
            <User size={28} weight="duotone" />
          </div>
          <div>
            <div className="overline mb-1 capitalize">{g.relationship_type}</div>
            <h1 className="font-heading font-black text-4xl tracking-tighter" data-testid="guardian-name">{g.first_name} {g.last_name || ""}</h1>
            <div className="mt-2 text-sm text-[var(--tinted-grey-500)] font-mono">{g.mobile_primary}{g.email ? ` · ${g.email}` : ""}</div>
          </div>
        </div>
        {!editing ? (
          <Button onClick={() => setEditing(true)} data-testid="btn-edit-guardian" className="rounded-full bg-[var(--ink)] hover:bg-[var(--klein)] text-white"><Pencil size={14} className="mr-1" /> Edit</Button>
        ) : (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { setEditing(false); load(); }} data-testid="btn-cancel-edit" className="rounded-full">Cancel</Button>
            <Button onClick={save} data-testid="btn-save-edit" className="rounded-full bg-[var(--klein)] text-white"><FloppyDisk size={14} className="mr-1" /> Save</Button>
          </div>
        )}
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="guardian-info">
          <div className="overline mb-3">Details</div>
          {editing ? (
            <div className="grid grid-cols-2 gap-4">
              <div><Label className="overline">First</Label><Input value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} className={field} data-testid="ge-first" /></div>
              <div><Label className="overline">Last</Label><Input value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} className={field} data-testid="ge-last" /></div>
              <div><Label className="overline">Relationship</Label>
                <Select value={form.relationship_type} onValueChange={v => setForm({ ...form, relationship_type: v })}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="ge-rel"><SelectValue /></SelectTrigger>
                  <SelectContent>{RELATIONSHIPS.map(r => <SelectItem key={r} value={r} data-testid={`ger-${r}`}>{r}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="overline">Mobile</Label><Input value={form.mobile_primary} onChange={e => setForm({ ...form, mobile_primary: e.target.value })} className={field} data-testid="ge-mobile" /></div>
              <div><Label className="overline">Alt mobile</Label><Input value={form.mobile_secondary} onChange={e => setForm({ ...form, mobile_secondary: e.target.value })} className={field} data-testid="ge-mobile2" /></div>
              <div><Label className="overline">Email</Label><Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className={field} data-testid="ge-email" /></div>
              <div><Label className="overline">Occupation</Label><Input value={form.occupation} onChange={e => setForm({ ...form, occupation: e.target.value })} className={field} data-testid="ge-occ" /></div>
              <div><Label className="overline">Employer</Label><Input value={form.employer} onChange={e => setForm({ ...form, employer: e.target.value })} className={field} data-testid="ge-emp" /></div>
            </div>
          ) : (
            <dl className="text-sm space-y-2">
              <Row label="Relationship" value={<span className="capitalize">{g.relationship_type}</span>} />
              <Row label="Mobile" value={<span className="font-mono">{g.mobile_primary}</span>} />
              <Row label="Alt mobile" value={g.mobile_secondary ? <span className="font-mono">{g.mobile_secondary}</span> : "—"} />
              <Row label="Email" value={g.email ? <span className="font-mono">{g.email}</span> : "—"} />
              <Row label="Occupation" value={g.occupation} />
              <Row label="Employer" value={g.employer} />
              <Row label="Emergency flag" value={g.emergency_contact_flag ? "Yes" : "No"} />
              <Row label="Family" value={g.family_id ? <Link to={`/school/families/${g.family_id}`} className="klein-underline text-[var(--klein)] font-mono text-xs">{g.family_id.slice(0, 8)}…</Link> : "—"} />
              <Row label="Status" value={g.status} />
            </dl>
          )}
        </div>

        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="guardian-students">
          <div className="overline mb-3">Linked students ({students.length})</div>
          {students.length === 0 ? (
            <div className="text-sm text-[var(--tinted-grey-500)]">Not linked to any students yet.</div>
          ) : (
            <div className="divide-y divide-[var(--tinted-grey-200)] -mx-2">
              {students.map(r => (
                <Link key={r.id} to={`/school/students/${r.student_id}`} className="flex items-center justify-between px-2 py-3 hover:bg-[var(--tinted-grey-100)]" data-testid={`gs-${r.id}`}>
                  <div className="flex items-center gap-3">
                    <GraduationCap size={18} weight="duotone" className="text-[var(--klein)]" />
                    <div>
                      <div className="font-heading font-semibold text-sm">{r.student?.first_name} {r.student?.last_name || ""}</div>
                      <div className="text-xs text-[var(--tinted-grey-500)] capitalize">
                        <span className="font-mono">{r.student?.admission_number}</span> · {r.relationship_type}
                        {r.student?.class_name ? ` · ${r.student.class_name}${r.student.section ? " " + r.student.section : ""}` : ""}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    {r.is_primary && <span className="text-[10px] uppercase tracking-widest bg-[var(--klein)] text-white px-1.5 py-0.5">primary</span>}
                    {r.is_emergency_contact && <span className="text-[10px] uppercase tracking-widest bg-[var(--accent-red)] text-white px-1.5 py-0.5">emergency</span>}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="grid grid-cols-2 py-1 border-b border-[var(--tinted-grey-100)] last:border-0">
      <dt className="overline text-[10px] self-center">{label}</dt>
      <dd>{value ?? "—"}</dd>
    </div>
  );
}
