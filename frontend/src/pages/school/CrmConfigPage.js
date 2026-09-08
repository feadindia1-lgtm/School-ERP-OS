import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function CrmConfigPage() {
  const [s, setS] = useState(null);
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/school/crm/settings"); setS(data);
      } catch (e) { toast.error(formatApiError(e)); }
    })();
  }, []);

  if (!s) return <div className="text-[var(--tinted-grey-500)]">Loading…</div>;

  const save = async (patch) => {
    try {
      const { data } = await api.patch("/school/crm/settings", patch);
      setS(data); toast.success("Saved");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const toggleDocRequirement = (idx, requirement) => {
    const next = [...s.doc_types];
    next[idx] = { ...next[idx], requirement };
    save({ doc_types: next });
  };

  return (
    <div data-testid="crm-config-page">
      <div className="overline mb-2">Front Porch · Configuration</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter">Admissions settings</h1>

      <div className="mt-10 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-[var(--tinted-grey-200)] p-6">
          <div className="overline mb-4">Pipeline stages</div>
          <div className="space-y-2" data-testid="config-stages">
            {s.pipeline_stages.map(st => (
              <div key={st.code} className="flex items-center gap-3 p-2 border border-[var(--tinted-grey-200)]" data-testid={`config-stage-${st.code}`}>
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: st.color }} />
                <span className="font-mono text-[10px] w-32 uppercase">{st.code}</span>
                <span className="text-sm">{st.label}</span>
                <span className="ml-auto text-xs text-[var(--tinted-grey-500)]">order {st.order}</span>
              </div>
            ))}
          </div>
          <div className="mt-3 text-xs text-[var(--tinted-grey-500)]">Custom stage editor arrives in a later prompt.</div>
        </div>

        <div className="bg-white border border-[var(--tinted-grey-200)] p-6">
          <div className="overline mb-4">Inquiry sources</div>
          <div className="flex flex-wrap gap-2" data-testid="config-sources">
            {s.sources.map(src => <span key={src} className="text-xs px-2 py-1 bg-[var(--tinted-grey-100)] uppercase tracking-widest">{src.replace(/_/g," ")}</span>)}
          </div>
        </div>

        <div className="bg-white border border-[var(--tinted-grey-200)] p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="overline">Document types</div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-[var(--tinted-grey-500)]">Block approval until required docs verified</span>
              <Switch checked={s.require_docs_for_approval} onCheckedChange={(v) => save({ require_docs_for_approval: v })} data-testid="config-require-docs" />
            </div>
          </div>
          <div className="divide-y divide-[var(--tinted-grey-200)]" data-testid="config-docs">
            {s.doc_types.map((dt, i) => (
              <div key={dt.code} className="py-3 flex items-center justify-between gap-3" data-testid={`config-doc-${dt.code}`}>
                <div>
                  <div className="font-heading font-semibold">{dt.label}</div>
                  <div className="text-xs text-[var(--tinted-grey-500)] font-mono">{dt.code}{dt.condition_note ? ` · ${dt.condition_note}` : ""}</div>
                </div>
                <Select value={dt.requirement} onValueChange={(v) => toggleDocRequirement(i, v)}>
                  <SelectTrigger className="rounded-none h-9 w-[160px]" data-testid={`config-doc-req-${dt.code}`}><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="required">Required</SelectItem>
                    <SelectItem value="optional">Optional</SelectItem>
                    <SelectItem value="conditional">Conditional</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
