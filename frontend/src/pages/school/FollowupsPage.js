import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { CheckCircle, Phone } from "@phosphor-icons/react";

const BUCKETS = [
  { key: "overdue", label: "Overdue" },
  { key: "today", label: "Today" },
  { key: "upcoming", label: "Upcoming" },
];

function FollowupRow({ f, onDone }) {
  const complete = async () => {
    const notes = window.prompt("Outcome / notes (optional)");
    if (notes === null) return;
    try { await api.patch(`/school/crm/followups/${f.id}`, { status: "completed", completion_notes: notes || undefined }); toast.success("Follow-up completed"); onDone(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  return (
    <div className="p-4 flex items-center justify-between gap-3 border-b border-[var(--tinted-grey-200)] last:border-0" data-testid={`fq-row-${f.id}`}>
      <div className="min-w-0">
        <Link to={`/school/admissions/inquiries/${f.lead_id}`} className="font-heading font-semibold hover:text-[var(--klein)]" data-testid={`fq-lead-${f.id}`}>{f.lead_name || "Inquiry"}</Link>
        <span className="font-mono text-[10px] text-[var(--tinted-grey-500)] ml-2">{f.inquiry_number}</span>
        <div className="text-xs text-[var(--tinted-grey-500)] mt-0.5">
          {f.title} · {f.channel.replace(/_/g, " ")} · due {new Date(f.due_at).toLocaleString()}
          {f.lead_stage && <> · <span className="uppercase tracking-widest">{f.lead_stage.replace(/_/g, " ")}</span></>}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {f.parent_mobile && <a href={`tel:${f.parent_mobile}`} className="text-xs font-mono inline-flex items-center gap-1" data-testid={`fq-call-${f.id}`}><Phone size={12} />{f.parent_mobile}</a>}
        <Button size="sm" variant="outline" className="rounded-none" onClick={complete} data-testid={`fq-complete-${f.id}`}><CheckCircle size={12} className="mr-1" />Done</Button>
      </div>
    </div>
  );
}

export default function FollowupsPage() {
  const [bucket, setBucket] = useState("overdue");
  const [rows, setRows] = useState([]);
  const [counts, setCounts] = useState({});
  const load = useCallback(async () => {
    try {
      const res = await Promise.all(BUCKETS.map((b) => api.get("/school/crm/followups", { params: { bucket: b.key } })));
      const map = Object.fromEntries(BUCKETS.map((b, i) => [b.key, res[i].data]));
      setCounts(Object.fromEntries(BUCKETS.map((b) => [b.key, map[b.key].length])));
      setRows(map[bucket]);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [bucket]);
  useEffect(() => { load(); }, [load]);
  return (
    <div data-testid="followups-page">
      <div className="overline mb-2">Front Porch · Follow-ups</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="followups-title">Follow-up queue</h1>
      <div className="mt-6 flex gap-2">
        {BUCKETS.map((b) => (
          <button key={b.key} onClick={() => setBucket(b.key)} data-testid={`fq-tab-${b.key}`}
            className={`px-4 py-2 text-sm border transition-colors ${bucket === b.key ? "bg-[var(--ink)] text-white border-[var(--ink)]" : "border-[var(--tinted-grey-300)] hover:border-[var(--ink)]"}`}>
            {b.label} <span className="font-mono text-xs ml-1" data-testid={`fq-count-${b.key}`}>{counts[b.key] ?? 0}</span>
          </button>
        ))}
      </div>
      <div className="mt-6 bg-white border border-[var(--tinted-grey-200)]" data-testid="fq-list">
        {rows.length === 0 && <div className="p-8 text-sm text-[var(--tinted-grey-500)]" data-testid="fq-empty">Nothing here.</div>}
        {rows.map((f) => <FollowupRow key={f.id} f={f} onDone={load} />)}
      </div>
    </div>
  );
}
