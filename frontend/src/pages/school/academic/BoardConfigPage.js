import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FloppyDisk, Plus, Trash } from "@phosphor-icons/react";
import { BOARD_PRESETS_LIST } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function BoardConfigPage() {
  const [cfg, setCfg] = useState(null);
  const [presets, setPresets] = useState({});
  const [newTerm, setNewTerm] = useState("");

  const load = async () => {
    try { const { data } = await api.get("/school/academic/board-config"); setCfg(data); setPresets(data.presets || {}); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    try {
      await api.patch("/school/academic/board-config", {
        board: cfg.board, class_label: cfg.class_label, section_label: cfg.section_label,
        terms: cfg.terms, marking_style: cfg.marking_style,
      });
      toast.success("Board config saved"); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const applyPreset = (board) => {
    const p = presets[board]; if (!p) return;
    setCfg({ ...cfg, board, class_label: p.class_label, section_label: p.section_label, terms: [...p.terms] });
  };
  const removeTerm = (i) => setCfg({ ...cfg, terms: cfg.terms.filter((_, idx) => idx !== i) });
  const addTerm = () => { if (!newTerm.trim()) return; setCfg({ ...cfg, terms: [...(cfg.terms || []), newTerm.trim()] }); setNewTerm(""); };

  if (!cfg) return <div className="text-[var(--tinted-grey-500)]">Loading…</div>;

  return (
    <div data-testid="board-config-page">
      <div>
        <div className="overline mb-2">Academic Framework</div>
        <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="bc-title">Board configuration</h1>
        <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Terminology & term structure applied across the school</div>
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="bc-labels">
          <div className="flex items-center justify-between mb-4">
            <div className="overline">Labels</div>
            <Button size="sm" onClick={save} data-testid="btn-save-config" className="rounded-none bg-[var(--klein)] text-white"><FloppyDisk size={12} className="mr-1"/> Save</Button>
          </div>
          <div className="space-y-4">
            <div>
              <Label className="overline">Board preset</Label>
              <Select value={cfg.board} onValueChange={applyPreset}>
                <SelectTrigger className="rounded-none h-10 mt-2" data-testid="bc-board-select"><SelectValue /></SelectTrigger>
                <SelectContent>{BOARD_PRESETS_LIST.map(b => <SelectItem key={b} value={b} data-testid={`bcb-${b}`}>{b}</SelectItem>)}</SelectContent>
              </Select>
              <div className="text-[10px] text-[var(--tinted-grey-500)] mt-1 uppercase tracking-widest">Choosing a preset resets labels + terms — override below</div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div><Label className="overline">Class label</Label><Input value={cfg.class_label} onChange={e => setCfg({ ...cfg, class_label: e.target.value })} className={field} data-testid="bc-class-label" /></div>
              <div><Label className="overline">Section label</Label><Input value={cfg.section_label} onChange={e => setCfg({ ...cfg, section_label: e.target.value })} className={field} data-testid="bc-section-label" /></div>
            </div>
            <div>
              <Label className="overline">Marking style</Label>
              <Select value={cfg.marking_style || "percentage"} onValueChange={v => setCfg({ ...cfg, marking_style: v })}>
                <SelectTrigger className="rounded-none h-10 mt-2" data-testid="bc-marking-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="percentage" data-testid="bcm-percentage">Percentage</SelectItem>
                  <SelectItem value="gpa" data-testid="bcm-gpa">GPA</SelectItem>
                  <SelectItem value="grades" data-testid="bcm-grades">Letter grades</SelectItem>
                </SelectContent>
              </Select>
              <div className="text-[10px] text-[var(--tinted-grey-500)] mt-1 uppercase tracking-widest">Consumed by Exams module (Prompt 6)</div>
            </div>
          </div>
        </div>

        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="bc-terms">
          <div className="overline mb-4">Term structure ({(cfg.terms || []).length})</div>
          <div className="space-y-2">
            {(cfg.terms || []).map((t, i) => (
              <div key={i} className="flex items-center gap-2 border-b border-[var(--tinted-grey-100)] py-1" data-testid={`term-${i}`}>
                <div className="text-sm flex-1">{t}</div>
                <button onClick={() => removeTerm(i)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)]" data-testid={`term-del-${i}`}><Trash size={12}/></button>
              </div>
            ))}
            <div className="flex items-center gap-2 pt-2">
              <Input value={newTerm} onChange={e => setNewTerm(e.target.value)} onKeyDown={e => { if (e.key === "Enter") addTerm(); }} placeholder="e.g. Term 3 / Semester 2" className="h-9 rounded-none" data-testid="term-input" />
              <Button size="sm" onClick={addTerm} data-testid="btn-add-term" className="rounded-none bg-[var(--ink)] text-white"><Plus size={12}/></Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
