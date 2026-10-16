import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export const EMPTY_FORM = {
  academic_year: "", class_requested: "", student_first_name: "", student_last_name: "", student_dob: "",
  student_gender: "", previous_school: "", parent_name: "", parent_relationship: "mother", parent_mobile: "",
  parent_email: "", address: "", form_answers: {},
};

const OPTIONAL = [
  { key: "student_dob", label: "Date of birth", type: "date" },
  { key: "student_gender", label: "Gender", type: "select", options: ["female", "male", "other"] },
  { key: "previous_school", label: "Previous school" },
  { key: "parent_email", label: "Parent email", type: "email" },
  { key: "address", label: "Home address", type: "textarea" },
];

function Pick({ value, onChange, options, testid, disabled, placeholder = "Select" }) {
  return (
    <Select value={value || ""} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger className="mt-2 rounded-none h-11 bg-white" data-testid={testid}><SelectValue placeholder={placeholder} /></SelectTrigger>
      <SelectContent>{options.map((o) => <SelectItem key={o} value={o} data-testid={`${testid}-opt-${o}`}>{o}</SelectItem>)}</SelectContent>
    </Select>
  );
}

function Field({ label, required, children }) {
  return <div><Label className="overline">{label}{required && <span className="text-[var(--accent-red)]"> *</span>}</Label>{children}</div>;
}

export function ApplicantFormFields({ form, setForm, config, disabled }) {
  const set = (k) => (e) => setForm({ ...form, [k]: e?.target ? e.target.value : e });
  const text = (k, type = "text") => (
    <Input type={type} value={form[k] || ""} onChange={set(k)} disabled={disabled} className="mt-2 rounded-none h-11 bg-white" data-testid={`af-${k}`} />
  );
  const answer = (q) => (v) => setForm({ ...form, form_answers: { ...form.form_answers, [q.key]: v?.target ? v.target.value : v } });
  return (
    <div className="space-y-8" data-testid="applicant-form-fields">
      <section className="grid sm:grid-cols-2 gap-5">
        <div className="sm:col-span-2 overline text-[var(--klein)]">Admission</div>
        <Field label="Academic year" required>{config.options.academic_years.length ? <Pick value={form.academic_year} onChange={set("academic_year")} options={config.options.academic_years} testid="af-academic_year" disabled={disabled} /> : text("academic_year")}</Field>
        <Field label="Class applying for" required>{config.options.classes.length ? <Pick value={form.class_requested} onChange={set("class_requested")} options={config.options.classes} testid="af-class_requested" disabled={disabled} /> : text("class_requested")}</Field>
      </section>
      <section className="grid sm:grid-cols-2 gap-5">
        <div className="sm:col-span-2 overline text-[var(--klein)]">Student</div>
        <Field label="First name" required>{text("student_first_name")}</Field>
        <Field label="Last name" required>{text("student_last_name")}</Field>
        {OPTIONAL.filter((f) => f.key.startsWith("student") || f.key === "previous_school").filter((f) => config.fields[f.key]?.enabled).map((f) => (
          <Field key={f.key} label={f.label} required={config.fields[f.key]?.required}>
            {f.type === "select" ? <Pick value={form[f.key]} onChange={set(f.key)} options={f.options} testid={`af-${f.key}`} disabled={disabled} /> : text(f.key, f.type)}
          </Field>
        ))}
      </section>
      <section className="grid sm:grid-cols-2 gap-5">
        <div className="sm:col-span-2 overline text-[var(--klein)]">Parent / guardian</div>
        <Field label="Full name" required>{text("parent_name")}</Field>
        <Field label="Relationship" required><Pick value={form.parent_relationship} onChange={set("parent_relationship")} options={["mother", "father", "guardian"]} testid="af-parent_relationship" disabled={disabled} /></Field>
        <Field label="Mobile number" required>{text("parent_mobile", "tel")}</Field>
        {config.fields.parent_email?.enabled && <Field label="Email" required={config.fields.parent_email.required}>{text("parent_email", "email")}</Field>}
        {config.fields.address?.enabled && (
          <div className="sm:col-span-2"><Field label="Home address" required={config.fields.address.required}>
            <Textarea rows={2} value={form.address || ""} onChange={set("address")} disabled={disabled} className="mt-2 rounded-none bg-white" data-testid="af-address" />
          </Field></div>
        )}
      </section>
      {config.custom_questions.length > 0 && (
        <section className="grid gap-5">
          <div className="overline text-[var(--klein)]">A few more questions</div>
          {config.custom_questions.map((q) => (
            <Field key={q.key} label={q.label} required={q.required}>
              {q.type === "select" ? <Pick value={form.form_answers?.[q.key]} onChange={answer(q)} options={q.options} testid={`af-q-${q.key}`} disabled={disabled} />
                : q.type === "textarea" ? <Textarea rows={3} value={form.form_answers?.[q.key] || ""} onChange={answer(q)} disabled={disabled} className="mt-2 rounded-none bg-white" data-testid={`af-q-${q.key}`} />
                : <Input value={form.form_answers?.[q.key] || ""} onChange={answer(q)} disabled={disabled} className="mt-2 rounded-none h-11 bg-white" data-testid={`af-q-${q.key}`} />}
            </Field>
          ))}
        </section>
      )}
    </div>
  );
}

export function toPayload(form) {
  const out = { ...form };
  Object.keys(out).forEach((k) => { if (out[k] === "") out[k] = null; });
  out.form_answers = form.form_answers || {};
  return out;
}

export function ApplyShell({ school, children }) {
  return (
    <div className="min-h-screen bg-[#F4F1EA]" data-testid="apply-shell">
      <header className="border-b border-[var(--ink)]/10 bg-white">
        <div className="max-w-3xl mx-auto px-5 py-5 flex items-center justify-between">
          <div>
            <div className="overline text-[10px]">Online admission</div>
            <div className="font-heading font-black text-2xl tracking-tight" data-testid="apply-school-name">{school?.name || "School"}</div>
          </div>
          <div className="text-[10px] uppercase tracking-widest text-[var(--tinted-grey-500)]">Secure form</div>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-5 py-10">{children}</main>
    </div>
  );
}
