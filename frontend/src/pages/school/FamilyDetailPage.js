import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Users, GraduationCap, User, Pencil, FloppyDisk } from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function FamilyDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [f, setF] = useState(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ family_name: "", notes: "" });

  const load = async () => {
    try { const { data } = await api.get(`/school/families/${id}`); setF(data); setForm({ family_name: data.family_name, notes: data.notes || "" }); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const save = async () => {
    try { await api.patch(`/school/families/${id}`, form); toast.success("Family updated"); setEditing(false); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  if (!f) return <div className="text-[var(--tinted-grey-500)]">Loading…</div>;

  const siblings = f.students || [];
  const guardians = f.guardians || [];

  return (
    <div data-testid="family-detail">
      <button onClick={() => navigate("/school/families")} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--tinted-grey-500)] hover:text-[var(--ink)]" data-testid="back-to-families">
        <ArrowLeft size={14} /> All families
      </button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-5">
          <div className="h-16 w-16 bg-[var(--klein)] text-white flex items-center justify-center">
            <Users size={28} weight="duotone" />
          </div>
          <div>
            <div className="overline mb-1">Family</div>
            <h1 className="font-heading font-black text-4xl tracking-tighter" data-testid="family-name">{f.family_name}</h1>
            <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">
              {siblings.length} student{siblings.length === 1 ? "" : "s"} · {guardians.length} guardian{guardians.length === 1 ? "" : "s"}
            </div>
          </div>
        </div>
        {!editing ? (
          <Button onClick={() => setEditing(true)} data-testid="btn-edit-family" className="rounded-full bg-[var(--ink)] hover:bg-[var(--klein)] text-white"><Pencil size={14} className="mr-1" /> Edit</Button>
        ) : (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { setEditing(false); load(); }} data-testid="btn-cancel-family" className="rounded-full">Cancel</Button>
            <Button onClick={save} data-testid="btn-save-family" className="rounded-full bg-[var(--klein)] text-white"><FloppyDisk size={14} className="mr-1" /> Save</Button>
          </div>
        )}
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="family-info">
          <div className="overline mb-3">Details</div>
          {editing ? (
            <div className="space-y-4">
              <div><Label className="overline">Family name</Label><Input value={form.family_name} onChange={e => setForm({ ...form, family_name: e.target.value })} className={field} data-testid="fe-name" /></div>
              <div><Label className="overline">Notes</Label><Input value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} className={field} data-testid="fe-notes" /></div>
            </div>
          ) : (
            <dl className="text-sm space-y-2">
              <Row label="Name" value={f.family_name} />
              <Row label="Notes" value={f.notes} />
              <Row label="Primary contact" value={f.primary_contact_guardian_id ? <Link to={`/school/guardians/${f.primary_contact_guardian_id}`} className="klein-underline text-[var(--klein)] font-mono text-xs">{f.primary_contact_guardian_id.slice(0, 8)}…</Link> : "—"} />
              <Row label="Created" value={f.created_at?.slice(0, 10)} />
            </dl>
          )}
        </div>

        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="family-students">
          <div className="overline mb-3">Siblings ({siblings.length})</div>
          {siblings.length === 0 ? (
            <div className="text-sm text-[var(--tinted-grey-500)]">No students linked to this family. From a student profile, set the family_id to link them here.</div>
          ) : (
            <div className="divide-y divide-[var(--tinted-grey-200)] -mx-2">
              {siblings.map(s => (
                <Link key={s.id} to={`/school/students/${s.id}`} className="flex items-center justify-between px-2 py-3 hover:bg-[var(--tinted-grey-100)]" data-testid={`fs-${s.id}`}>
                  <div className="flex items-center gap-3">
                    <GraduationCap size={18} weight="duotone" className="text-[var(--klein)]" />
                    <div>
                      <div className="font-heading font-semibold text-sm">{s.first_name} {s.last_name || ""}</div>
                      <div className="text-xs text-[var(--tinted-grey-500)]">
                        <span className="font-mono">{s.admission_number}</span>
                        {s.class_name ? ` · ${s.class_name}${s.section ? " " + s.section : ""}` : ""}
                      </div>
                    </div>
                  </div>
                  <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${s.status === "ACTIVE" ? "bg-[var(--klein)] text-white" : "bg-[var(--tinted-grey-100)]"}`}>{s.status}</span>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="family-guardians">
          <div className="overline mb-3">Guardians ({guardians.length})</div>
          {guardians.length === 0 ? (
            <div className="text-sm text-[var(--tinted-grey-500)]">No guardians attached. Guardians can be linked to a family from the guardian record.</div>
          ) : (
            <div className="divide-y divide-[var(--tinted-grey-200)] -mx-2">
              {guardians.map(g => (
                <Link key={g.id} to={`/school/guardians/${g.id}`} className="flex items-center justify-between px-2 py-3 hover:bg-[var(--tinted-grey-100)]" data-testid={`fg-${g.id}`}>
                  <div className="flex items-center gap-3">
                    <User size={18} weight="duotone" className="text-[var(--klein)]" />
                    <div>
                      <div className="font-heading font-semibold text-sm">{g.first_name} {g.last_name || ""}</div>
                      <div className="text-xs text-[var(--tinted-grey-500)] capitalize">{g.relationship_type} · <span className="font-mono">{g.mobile_primary}</span></div>
                    </div>
                  </div>
                  {f.primary_contact_guardian_id === g.id && <span className="text-[10px] uppercase tracking-widest bg-[var(--klein)] text-white px-1.5 py-0.5">contact</span>}
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
