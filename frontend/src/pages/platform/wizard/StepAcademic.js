import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { X } from "@phosphor-icons/react";
import { useState } from "react";

const field = "mt-2 h-11 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";
const DAYS = [["mon","Mon"],["tue","Tue"],["wed","Wed"],["thu","Thu"],["fri","Fri"],["sat","Sat"],["sun","Sun"]];

function Chips({ value, onChange, placeholder, testid }) {
  const [text, setText] = useState("");
  const add = () => {
    if (!text.trim()) return;
    if (value.includes(text.trim())) { setText(""); return; }
    onChange([...value, text.trim()]);
    setText("");
  };
  return (
    <div>
      <div className="flex gap-2">
        <Input data-testid={testid} value={text} onChange={(e)=>setText(e.target.value)} onKeyDown={(e)=>{if(e.key==="Enter"){e.preventDefault();add();}}} placeholder={placeholder} className={field} />
        <button type="button" onClick={add} className="mt-2 h-11 px-4 bg-[var(--ink)] text-white hover:bg-[var(--klein)] transition-colors" data-testid={`${testid}-add`}>Add</button>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {value.map((c) => (
          <Badge key={c} variant="outline" className="rounded-none border-[var(--tinted-grey-300)]" data-testid={`${testid}-chip-${c}`}>
            {c}
            <button onClick={() => onChange(value.filter(x => x !== c))} className="ml-1 hover:text-[var(--accent-red)]" aria-label={`Remove ${c}`}>
              <X size={10} />
            </button>
          </Badge>
        ))}
      </div>
    </div>
  );
}

export default function StepAcademic({ value, set }) {
  const v = value.academic;
  const s = set("academic");
  const toggleDay = (d) => {
    const next = v.working_days.includes(d) ? v.working_days.filter(x => x !== d) : [...v.working_days, d];
    s({ working_days: next, school_week: next.length });
  };
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="md:col-span-2"><Label className="overline">Academic year name</Label><Input data-testid="w-ay-name" required value={v.academic_year_name} onChange={(e)=>s({academic_year_name:e.target.value})} className={field} /></div>
      <div><Label className="overline">Start date</Label><Input data-testid="w-ay-start" type="date" value={v.start_date} onChange={(e)=>s({start_date:e.target.value})} className={field} /></div>
      <div><Label className="overline">End date</Label><Input data-testid="w-ay-end" type="date" value={v.end_date} onChange={(e)=>s({end_date:e.target.value})} className={field} /></div>
      <div className="md:col-span-2">
        <Label className="overline">Classes offered</Label>
        <Chips value={v.classes_offered} onChange={(x)=>s({classes_offered:x})} placeholder="Nursery, LKG, 1, 2, 3…" testid="w-classes" />
      </div>
      <div className="md:col-span-2">
        <Label className="overline">Sections</Label>
        <Chips value={v.sections} onChange={(x)=>s({sections:x})} placeholder="A, B, C…" testid="w-sections" />
      </div>
      <div>
        <Label className="overline">Medium</Label>
        <Select value={v.medium} onValueChange={(x)=>s({medium:x})}>
          <SelectTrigger data-testid="w-medium" className="mt-2 rounded-none h-11 border-x-0 border-t-0 border-b-2 border-[var(--ink)]"><SelectValue /></SelectTrigger>
          <SelectContent>
            {["english","hindi","tamil","kannada","telugu","marathi","french","spanish","other"].map(m => (
              <SelectItem key={m} value={m} data-testid={`w-medium-${m}`}>{m}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="overline">School week</Label>
        <div className="mt-2 h-11 flex items-end font-heading font-black text-2xl tabular">{v.school_week} days</div>
      </div>
      <div className="md:col-span-2">
        <Label className="overline">Working days</Label>
        <div className="mt-3 flex flex-wrap gap-2" data-testid="w-working-days">
          {DAYS.map(([k,l]) => {
            const on = v.working_days.includes(k);
            return (
              <button key={k} type="button" onClick={()=>toggleDay(k)} data-testid={`w-day-${k}`} className={`px-3 py-1.5 text-xs font-mono uppercase tracking-widest transition-colors ${on ? "bg-[var(--ink)] text-white" : "bg-white border border-[var(--tinted-grey-300)] text-[var(--tinted-grey-500)] hover:border-[var(--ink)]"}`}>
                {l}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
