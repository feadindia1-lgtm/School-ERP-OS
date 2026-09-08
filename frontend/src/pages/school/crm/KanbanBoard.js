import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

export default function KanbanBoard({ leads, stages, reload }) {
  const [dragOver, setDragOver] = useState(null);
  const grouped = useMemo(() => {
    const g = {};
    stages.forEach(s => { g[s.code] = []; });
    leads.forEach(l => { (g[l.stage] = g[l.stage] || []).push(l); });
    return g;
  }, [leads, stages]);

  const onDrop = async (leadId, newStage) => {
    setDragOver(null);
    try {
      await api.post(`/school/crm/leads/${leadId}/stage`, { stage: newStage });
      toast.success(`Moved to ${newStage}`);
      reload?.();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="mt-6 flex gap-3 overflow-x-auto pb-4" data-testid="kanban-board">
      {stages.map(s => {
        const cards = grouped[s.code] || [];
        const isOver = dragOver === s.code;
        return (
          <div
            key={s.code}
            data-testid={`kanban-column-${s.code}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(s.code); }}
            onDragLeave={() => setDragOver(v => v === s.code ? null : v)}
            onDrop={(e) => onDrop(e.dataTransfer.getData("lead-id"), s.code)}
            className={`shrink-0 w-[300px] bg-[var(--tinted-grey-50)] border ${isOver ? "border-[var(--klein)]" : "border-[var(--tinted-grey-200)]"} min-h-[300px]`}
          >
            <div className="p-3 border-b border-[var(--tinted-grey-200)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color || "var(--klein)" }} />
                <div className="font-heading font-bold text-sm">{s.label}</div>
              </div>
              <span className="font-mono text-xs text-[var(--tinted-grey-500)]">{cards.length}</span>
            </div>
            <div className="p-2 space-y-2">
              {cards.length === 0 && <div className="text-xs text-[var(--tinted-grey-400)] p-3">No leads.</div>}
              {cards.map(l => <LeadCard key={l.id} lead={l} />)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LeadCard({ lead }) {
  const nav = useNavigate();
  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData("lead-id", lead.id)}
      onClick={() => nav(`/school/admissions/inquiries/${lead.id}`)}
      className="bg-white border border-[var(--tinted-grey-200)] p-3 cursor-pointer hover:border-[var(--klein)] transition-colors"
      data-testid={`kanban-card-${lead.inquiry_number}`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-mono text-[10px] text-[var(--klein)]">{lead.inquiry_number}</span>
        <span className={`text-[9px] uppercase tracking-widest px-1.5 py-0.5 ${lead.priority === "urgent" ? "bg-[var(--accent-red)] text-white" : lead.priority === "high" ? "bg-[var(--accent-yellow)]" : "bg-[var(--tinted-grey-100)]"}`}>{lead.priority}</span>
      </div>
      <div className="font-heading font-semibold text-sm">{lead.student_first_name} {lead.student_last_name}</div>
      <div className="text-xs text-[var(--tinted-grey-500)] mt-1">{lead.class_seeking || "—"} · {lead.academic_year || "—"}</div>
      <div className="mt-2 text-xs">
        <div>{lead.parent_name}</div>
        <div className="font-mono text-[10px] text-[var(--tinted-grey-500)]">{lead.parent_mobile}</div>
      </div>
      {lead.next_followup_at && <div className="mt-2 text-[10px] font-mono text-[var(--klein)]">↻ {lead.next_followup_at.slice(0,10)}</div>}
    </div>
  );
}
