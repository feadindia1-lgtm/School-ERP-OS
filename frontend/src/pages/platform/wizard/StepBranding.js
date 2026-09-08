import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const field = "mt-2 h-11 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

function ColorInput({ label, value, onChange, testid }) {
  return (
    <div>
      <Label className="overline">{label}</Label>
      <div className="mt-2 flex items-center gap-3 border-b-2 border-[var(--ink)]">
        <input type="color" value={value} onChange={(e)=>onChange(e.target.value)} className="h-10 w-14 border-0 bg-transparent cursor-pointer p-0" data-testid={`${testid}-picker`} />
        <input type="text" value={value} onChange={(e)=>onChange(e.target.value)} data-testid={testid} className="flex-1 h-10 font-mono text-sm bg-transparent outline-none" />
      </div>
    </div>
  );
}

export default function StepBranding({ value, set }) {
  const v = value.branding;
  const s = set("branding");
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div><Label className="overline">Logo URL</Label><Input data-testid="w-logo" value={v.logo_url} onChange={(e)=>s({logo_url:e.target.value})} className={field} /></div>
      <div><Label className="overline">Favicon URL</Label><Input data-testid="w-favicon" value={v.favicon_url} onChange={(e)=>s({favicon_url:e.target.value})} className={field} /></div>

      <ColorInput label="Primary colour" value={v.primary_color} onChange={(x)=>s({primary_color:x})} testid="w-primary" />
      <ColorInput label="Secondary colour" value={v.secondary_color} onChange={(x)=>s({secondary_color:x})} testid="w-secondary" />
      <ColorInput label="Accent colour" value={v.accent_color} onChange={(x)=>s({accent_color:x})} testid="w-accent" />

      <div>
        <Label className="overline">Theme mode</Label>
        <Select value={v.theme_mode} onValueChange={(x)=>s({theme_mode:x})}>
          <SelectTrigger data-testid="w-theme" className="mt-2 rounded-none h-11 border-x-0 border-t-0 border-b-2 border-[var(--ink)]"><SelectValue /></SelectTrigger>
          <SelectContent>
            {["light","dark","system"].map(t=><SelectItem key={t} value={t} data-testid={`w-theme-${t}`}>{t}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="overline">Typography</Label>
        <Select value={v.typography} onValueChange={(x)=>s({typography:x})}>
          <SelectTrigger data-testid="w-typography" className="mt-2 rounded-none h-11 border-x-0 border-t-0 border-b-2 border-[var(--ink)]"><SelectValue /></SelectTrigger>
          <SelectContent>
            {[["cabinet_grotesk","Cabinet Grotesk"],["plex","IBM Plex"],["inter","Inter"],["serif","Serif"]].map(([k,l])=>(<SelectItem key={k} value={k} data-testid={`w-typography-${k}`}>{l}</SelectItem>))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="overline">Dashboard style</Label>
        <Select value={v.dashboard_style} onValueChange={(x)=>s({dashboard_style:x})}>
          <SelectTrigger data-testid="w-dashboard-style" className="mt-2 rounded-none h-11 border-x-0 border-t-0 border-b-2 border-[var(--ink)]"><SelectValue /></SelectTrigger>
          <SelectContent>
            {["modern","classic","dense"].map(x=><SelectItem key={x} value={x} data-testid={`w-dashboard-style-${x}`}>{x}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="md:col-span-2 mt-3 p-6 border border-[var(--tinted-grey-200)] bg-[var(--paper)]" data-testid="w-brand-preview">
        <div className="overline mb-3">Preview</div>
        <div className="flex items-center gap-4 flex-wrap">
          <div className="h-14 w-14 flex items-center justify-center font-heading font-black text-white" style={{ backgroundColor: v.primary_color }}>OK</div>
          <div>
            <div className="font-heading font-black text-2xl" style={{ color: v.secondary_color }}>{value.institution.school_name || "Your school"}</div>
            <div className="mt-1 inline-block px-2 py-0.5 text-xs" style={{ backgroundColor: v.accent_color, color: v.secondary_color }}>{value.institution.board?.toUpperCase() || "BOARD"}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
