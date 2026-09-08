import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, CheckCircle, Buildings, MapTrifold, GraduationCap, User, Palette, PuzzlePiece } from "@phosphor-icons/react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import StepInstitution from "./wizard/StepInstitution";
import StepContact from "./wizard/StepContact";
import StepAcademic from "./wizard/StepAcademic";
import StepAdministrator from "./wizard/StepAdministrator";
import StepBranding from "./wizard/StepBranding";
import StepModules from "./wizard/StepModules";

const STEPS = [
  { key: "institution", label: "Institution", icon: Buildings, Comp: StepInstitution },
  { key: "contact", label: "Contact", icon: MapTrifold, Comp: StepContact },
  { key: "academic", label: "Academic", icon: GraduationCap, Comp: StepAcademic },
  { key: "administrator", label: "Administrator", icon: User, Comp: StepAdministrator },
  { key: "branding", label: "Branding", icon: Palette, Comp: StepBranding },
  { key: "modules", label: "Modules", icon: PuzzlePiece, Comp: StepModules },
];

const initial = {
  institution: { school_name: "", slug: "", short_name: "", school_code: "", board: "cbse", school_type: "k12" },
  contact: { address_line: "", city: "", district: "", state: "", pin: "", country: "India", phone: "", email: "", website: "" },
  academic: { academic_year_name: "AY 2026-27", start_date: "2026-04-01", end_date: "2027-03-31", classes_offered: [], sections: ["A", "B"], medium: "english", working_days: ["mon", "tue", "wed", "thu", "fri"], school_week: 5 },
  administrator: { full_name: "", email: "", mobile: "", temp_password: "", send_invite: true },
  branding: { logo_url: "", favicon_url: "", primary_color: "#002FA7", secondary_color: "#0A0A0C", accent_color: "#FFCC00", theme_mode: "light", typography: "cabinet_grotesk", dashboard_style: "modern" },
  modules: { crm: true, attendance: true, fees: true, payroll: true, examinations: true, curriculum: true, transport: false, library: false, communication: true, ai_assistance: false },
  plan: "trial",
};

function validateStep(idx, data) {
  const s = data;
  if (idx === 0) {
    if (!s.institution.school_name || s.institution.school_name.trim().length < 2) return "School name is required";
    if (!/^[a-z0-9-]{2,64}$/.test(s.institution.slug)) return "Slug must be lowercase letters, digits or hyphen (2-64)";
  }
  if (idx === 1) {
    if (!s.contact.email) return "Contact email is required";
  }
  if (idx === 2) {
    if (!s.academic.academic_year_name) return "Academic year name is required";
  }
  if (idx === 3) {
    if (!s.administrator.full_name || s.administrator.full_name.trim().length < 2) return "Administrator name is required";
    if (!s.administrator.email) return "Administrator email is required";
    if (s.administrator.temp_password && s.administrator.temp_password.length < 8) return "Password must be at least 8 characters";
  }
  return null;
}

export default function PlatformSchoolNewPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [data, setData] = useState(initial);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const set = (key) => (patch) => setData((d) => ({ ...d, [key]: { ...d[key], ...patch } }));

  const next = () => {
    const err = validateStep(step, data);
    if (err) return toast.error(err);
    setStep((s) => Math.min(STEPS.length - 1, s + 1));
  };
  const back = () => setStep((s) => Math.max(0, s - 1));

  const submit = async () => {
    // final validation across steps
    for (let i = 0; i < STEPS.length; i++) {
      const err = validateStep(i, data);
      if (err) { setStep(i); return toast.error(err); }
    }
    setSubmitting(true);
    try {
      const payload = {
        institution: data.institution,
        contact: { ...data.contact, email: data.contact.email || data.administrator.email },
        academic: data.academic,
        administrator: { ...data.administrator, temp_password: data.administrator.temp_password || null },
        branding: data.branding,
        modules: data.modules,
        plan: data.plan,
      };
      const { data: res } = await api.post("/platform/schools", payload);
      setResult(res);
      toast.success("School onboarded");
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSubmitting(false); }
  };

  if (result) {
    return (
      <div data-testid="wizard-success" className="max-w-2xl">
        <div className="overline mb-3">Onboarded</div>
        <h1 className="font-heading font-black text-4xl tracking-tighter">{result.tenant.name} is live.</h1>
        <div className="mt-8 bg-white border border-[var(--tinted-grey-200)] p-8">
          <div className="flex items-center gap-3">
            <CheckCircle size={22} weight="fill" className="text-[var(--klein)]" />
            <div className="font-heading font-bold">Tenant provisioned</div>
          </div>
          <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
            <div><dt className="overline">Slug</dt><dd className="font-mono mt-1">{result.tenant.slug}</dd></div>
            <div><dt className="overline">Plan</dt><dd className="mt-1 uppercase tracking-widest text-xs">{result.tenant.plan}</dd></div>
            <div><dt className="overline">Administrator</dt><dd className="font-mono mt-1">{result.administrator.email}</dd></div>
            <div><dt className="overline">Status</dt><dd className="mt-1 capitalize">{result.tenant.status}</dd></div>
          </dl>
          {result.temp_password && (
            <div className="mt-6 bg-[var(--tinted-grey-100)] border border-[var(--tinted-grey-200)] p-4" data-testid="wizard-temp-password">
              <div className="overline mb-2">Temporary password</div>
              <code className="font-mono text-lg text-[var(--klein)]">{result.temp_password}</code>
              <div className="text-xs mt-2 text-[var(--tinted-grey-500)]">Share this once with the administrator. They must reset on first login.</div>
            </div>
          )}
        </div>
        <div className="mt-6 flex gap-3">
          <Button data-testid="wizard-open-school" onClick={() => navigate(`/platform/schools/${result.tenant.id}`)} className="rounded-full bg-[var(--klein)] hover:bg-[var(--klein-hover)] text-white transition-colors">
            Open school
          </Button>
          <Button data-testid="wizard-onboard-another" variant="outline" onClick={() => { setResult(null); setStep(0); setData(initial); }} className="rounded-full">
            Onboard another
          </Button>
        </div>
      </div>
    );
  }

  const Step = STEPS[step].Comp;

  return (
    <div data-testid="wizard-page" className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      {/* Stepper */}
      <aside className="lg:col-span-3">
        <div className="overline mb-3">Onboard</div>
        <h1 className="font-heading font-black text-3xl tracking-tighter mb-8">New school</h1>
        <ol className="space-y-2" data-testid="wizard-steps">
          {STEPS.map((s, i) => {
            const active = i === step;
            const done = i < step;
            return (
              <li key={s.key} data-testid={`wizard-step-${s.key}`} className={`flex items-center gap-3 p-3 border-l-2 ${active ? "border-[var(--klein)] bg-white" : done ? "border-[var(--klein)]/50" : "border-[var(--tinted-grey-200)]"}`}>
                <div className={`h-7 w-7 flex items-center justify-center text-xs font-mono ${done ? "bg-[var(--klein)] text-white" : active ? "bg-[var(--ink)] text-white" : "bg-[var(--tinted-grey-100)]"}`}>
                  {done ? <CheckCircle size={14} weight="fill" /> : i + 1}
                </div>
                <span className={`text-sm ${active || done ? "font-semibold" : "text-[var(--tinted-grey-500)]"}`}>{s.label}</span>
              </li>
            );
          })}
        </ol>
      </aside>

      {/* Step content */}
      <div className="lg:col-span-9 min-w-0">
        <div className="bg-white border border-[var(--tinted-grey-200)] p-8 lg:p-10">
          <AnimatePresence mode="wait">
            <motion.div key={step} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.25 }}>
              <div className="flex items-center gap-3 mb-2">
                {(() => { const I = STEPS[step].icon; return <I size={22} weight="duotone" className="text-[var(--klein)]" />; })()}
                <div className="overline">Step {step + 1} of {STEPS.length}</div>
              </div>
              <h2 className="font-heading font-black text-3xl tracking-tighter mb-8">{STEPS[step].label}</h2>
              <Step value={data} set={set} setPlan={(p) => setData(d => ({ ...d, plan: p }))} />
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="mt-6 flex items-center justify-between">
          <Button data-testid="wizard-back" onClick={back} disabled={step === 0} variant="ghost" className="rounded-full">
            <ArrowLeft size={16} className="mr-2" /> Back
          </Button>
          {step < STEPS.length - 1 ? (
            <Button data-testid="wizard-next" onClick={next} className="rounded-full bg-[var(--ink)] hover:bg-[var(--klein)] text-white transition-colors">
              Next <ArrowRight size={16} className="ml-2" />
            </Button>
          ) : (
            <Button data-testid="wizard-submit" onClick={submit} disabled={submitting} className="rounded-full bg-[var(--klein)] hover:bg-[var(--klein-hover)] text-white transition-colors">
              {submitting ? "Onboarding…" : "Onboard school"} <ArrowRight size={16} className="ml-2" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
