import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import {
  ChalkboardTeacher, Calendar, Coins, ClipboardText, Books, EnvelopeSimple, Sparkle, Bus, BookOpen, Wall,
} from "@phosphor-icons/react";

const MODULES = [
  { k: "crm", label: "CRM (Front Porch)", desc: "Inquiry → Application → Conversion", icon: Wall, future: false },
  { k: "attendance", label: "Attendance", desc: "Class-teacher & biometric", icon: ChalkboardTeacher, future: false },
  { k: "fees", label: "Fees", desc: "Structures, collect, refunds", icon: Coins, future: false },
  { k: "payroll", label: "Payroll", desc: "Salary components + statutory", icon: ClipboardText, future: false },
  { k: "examinations", label: "Examinations", desc: "Marks, report cards", icon: BookOpen, future: false },
  { k: "curriculum", label: "Curriculum tracker", desc: "Syllabus + lesson plans", icon: Books, future: false },
  { k: "communication", label: "Communication", desc: "Announcements & notifications", icon: EnvelopeSimple, future: false },
  { k: "ai_assistance", label: "AI Assistance", desc: "AI copilots across modules", icon: Sparkle, future: false },
  { k: "transport", label: "Transport", desc: "Coming later", icon: Bus, future: true },
  { k: "library", label: "Library", desc: "Coming later", icon: Calendar, future: true },
];

export default function StepModules({ value, set, setPlan }) {
  const v = value.modules;
  const s = set("modules");
  return (
    <div>
      <div className="mb-8">
        <Label className="overline">Subscription plan</Label>
        <div className="mt-3">
          <Select value={value.plan} onValueChange={(p)=>setPlan(p)}>
            <SelectTrigger data-testid="w-plan" className="rounded-none h-11 w-full md:w-[280px] border-x-0 border-t-0 border-b-2 border-[var(--ink)]"><SelectValue /></SelectTrigger>
            <SelectContent>
              {[["trial","Trial · 30 days free"],["starter","Starter · $49/mo"],["standard","Standard · $149/mo"],["premium","Premium · $349/mo"],["enterprise","Enterprise · $899/mo"]].map(([k,l])=>(
                <SelectItem key={k} value={k} data-testid={`w-plan-${k}`}>{l}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--tinted-grey-200)] border border-[var(--tinted-grey-200)]" data-testid="w-modules">
        {MODULES.map(({ k, label, desc, icon: Icon, future }) => (
          <label key={k} className={`bg-white p-5 flex items-start gap-4 cursor-pointer ${future ? "opacity-70" : ""}`} data-testid={`w-module-${k}`}>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <Icon size={18} weight="duotone" className="text-[var(--klein)]" />
                <div className="font-heading font-bold">{label}</div>
                {future && <span className="text-[10px] uppercase tracking-widest text-[var(--tinted-grey-400)]">soon</span>}
              </div>
              <div className="mt-1 text-sm text-[var(--tinted-grey-500)]">{desc}</div>
            </div>
            <Switch checked={!!v[k]} onCheckedChange={(x)=>s({[k]:x})} data-testid={`w-module-toggle-${k}`} />
          </label>
        ))}
      </div>
    </div>
  );
}
