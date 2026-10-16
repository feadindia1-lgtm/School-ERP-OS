import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Copy, Plus, Trash } from "@phosphor-icons/react";

const FIELD_LABELS = { student_dob: "Date of birth", student_gender: "Gender", previous_school: "Previous school", parent_email: "Parent email", address: "Home address" };
const csv = (a) => (a || []).join(", ");
const uncsv = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);

function CsvInput({ value, onChange, testid, ...rest }) {
  const [raw, setRaw] = useState(csv(value));
  return <Input {...rest} value={raw} onChange={(e) => setRaw(e.target.value)} onBlur={() => onChange(uncsv(raw))} data-testid={testid} />;
}

function FieldToggles({ fields, onChange }) {
  return (
    <div className="divide-y divide-[var(--tinted-grey-200)]" data-testid="fc-fields">
      {Object.entries(FIELD_LABELS).map(([k, label]) => {
        const f = fields[k] || { enabled: true, required: false };
        return (
          <div key={k} className="py-2 flex items-center justify-between text-sm">
            <span>{label}</span>
            <div className="flex items-center gap-4 text-xs">
              <label className="flex items-center gap-2">Show <Switch checked={f.enabled} onCheckedChange={(v) => onChange(k, { ...f, enabled: v, required: v && f.required })} data-testid={`fc-${k}-enabled`} /></label>
              <label className="flex items-center gap-2">Required <Switch checked={f.required} disabled={!f.enabled} onCheckedChange={(v) => onChange(k, { ...f, required: v })} data-testid={`fc-${k}-required`} /></label>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Questions({ items, onChange }) {
  const upd = (i, patch) => onChange(items.map((q, j) => (j === i ? { ...q, ...patch } : q)));
  return (
    <div className="space-y-3" data-testid="fc-questions">
      {items.map((q, i) => (
        <div key={i} className="grid sm:grid-cols-12 gap-2 items-center" data-testid={`fc-q-${i}`}>
          <Input className="sm:col-span-5 rounded-none" placeholder="Question" value={q.label} onChange={(e) => upd(i, { label: e.target.value })} data-testid={`fc-q-label-${i}`} />
          <select className="sm:col-span-2 h-10 border border-[var(--tinted-grey-300)] text-sm px-2" value={q.type} onChange={(e) => upd(i, { type: e.target.value })} data-testid={`fc-q-type-${i}`}>
            <option value="text">Short text</option><option value="textarea">Long text</option><option value="select">Choice</option>
          </select>
          <CsvInput className="sm:col-span-3 rounded-none" placeholder="Options (comma)" disabled={q.type !== "select"} value={q.options} onChange={(o) => upd(i, { options: o })} testid={`fc-q-options-${i}`} />
          <label className="sm:col-span-1 text-xs flex items-center gap-1"><input type="checkbox" checked={!!q.required} onChange={(e) => upd(i, { required: e.target.checked })} data-testid={`fc-q-required-${i}`} />Req.</label>
          <button className="sm:col-span-1 text-[var(--tinted-grey-500)] hover:text-[var(--accent-red)]" onClick={() => onChange(items.filter((_, j) => j !== i))} data-testid={`fc-q-del-${i}`}><Trash size={14} /></button>
        </div>
      ))}
      <Button variant="outline" size="sm" className="rounded-none" onClick={() => onChange([...items, { label: "", type: "text", options: [], required: false }])} data-testid="fc-q-add"><Plus size={12} className="mr-1" />Add question</Button>
    </div>
  );
}

function Panel({ title, children }) {
  return <div className="bg-white border border-[var(--tinted-grey-200)] p-5"><div className="overline mb-3">{title}</div>{children}</div>;
}

export default function AdmissionFormConfigPage() {
  const [cfg, setCfg] = useState(null);
  const [feeRule, setFeeRule] = useState(true);
  useEffect(() => {
    Promise.all([api.get("/school/admissions/form-config"), api.get("/school/crm/settings")])
      .then(([c, s]) => { setCfg(c.data); setFeeRule(s.data.require_fee_before_conversion); })
      .catch((e) => toast.error(formatApiError(e)));
  }, []);
  if (!cfg) return <div className="text-[var(--tinted-grey-500)]">Loading…</div>;
  const url = `${window.location.origin}${cfg.public_path}`;
  const save = async () => {
    if (document.activeElement) document.activeElement.blur();
    await new Promise((r) => setTimeout(r, 0));
    try {
      const { data } = await api.put("/school/admissions/form-config", cfg);
      await api.patch("/school/crm/settings", { require_fee_before_conversion: feeRule });
      setCfg(data); toast.success("Admission form saved");
    } catch (e) { toast.error(formatApiError(e)); }
  };
  return (
    <div data-testid="form-config-page" className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Front Porch · Online form</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="fc-title">Admission form</h1>
        </div>
        <Button onClick={save} className="rounded-full bg-[var(--klein)] text-white" data-testid="fc-save">Save changes</Button>
      </div>
      <Panel title="Public link">
        <div className="flex items-center gap-3 flex-wrap">
          <label className="flex items-center gap-2 text-sm"><Switch checked={cfg.enabled} onCheckedChange={(v) => setCfg({ ...cfg, enabled: v })} data-testid="fc-enabled" />Accept online applications</label>
          <Input readOnly value={url} className="rounded-none font-mono text-xs max-w-md" data-testid="fc-public-url" onFocus={(e) => e.target.select()} />
          <Button variant="outline" size="sm" className="rounded-none" onClick={() => navigator.clipboard.writeText(url).then(() => toast.success("Copied"))} data-testid="fc-copy"><Copy size={14} /></Button>
          <a href={cfg.public_path} target="_blank" rel="noreferrer" className="text-xs underline" data-testid="fc-preview">Preview →</a>
        </div>
      </Panel>
      <div className="grid lg:grid-cols-2 gap-6">
        <Panel title="Intro & options">
          <Label className="overline">Intro text</Label>
          <Textarea rows={3} value={cfg.intro_text || ""} onChange={(e) => setCfg({ ...cfg, intro_text: e.target.value })} className="mt-2 rounded-none" data-testid="fc-intro" />
          <Label className="overline mt-4 block">Classes offered (comma separated, blank = all classes)</Label>
          <CsvInput value={cfg.classes} onChange={(v) => setCfg({ ...cfg, classes: v })} placeholder={csv(cfg.options.classes)} className="mt-2 rounded-none" testid="fc-classes" />
          <Label className="overline mt-4 block">Academic years (blank = all open years)</Label>
          <CsvInput value={cfg.academic_years} onChange={(v) => setCfg({ ...cfg, academic_years: v })} placeholder={csv(cfg.options.academic_years)} className="mt-2 rounded-none" testid="fc-years" />
          <Label className="overline mt-4 block">Applicant link valid for (days)</Label>
          <Input type="number" min={1} max={90} value={cfg.link_expiry_days} onChange={(e) => setCfg({ ...cfg, link_expiry_days: Number(e.target.value) })} className="mt-2 rounded-none w-28" data-testid="fc-expiry" />
        </Panel>
        <Panel title="Optional fields">
          <FieldToggles fields={cfg.fields} onChange={(k, v) => setCfg({ ...cfg, fields: { ...cfg.fields, [k]: v } })} />
          <div className="overline mt-6 mb-2">Admission rule</div>
          <label className="flex items-center gap-2 text-sm"><Switch checked={feeRule} onCheckedChange={setFeeRule} data-testid="fc-fee-rule" />Require admission fee received before converting to a student</label>
        </Panel>
      </div>
      <Panel title="Custom questions"><Questions items={cfg.custom_questions} onChange={(q) => setCfg({ ...cfg, custom_questions: q })} /></Panel>
    </div>
  );
}
