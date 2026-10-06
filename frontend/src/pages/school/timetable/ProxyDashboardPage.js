/**
 * Proxy Dashboard — Prompt 7.
 *
 * Shows absent teachers for a chosen date, their affected periods, and
 * ranked substitute recommendations.  Admin/principal picks a candidate
 * and the system creates a pending substitution; the configured approver
 * (default: same role) can approve it, which overlays the daily
 * timetable without mutating the master.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { ArrowClockwise, UserSwitch, CheckCircle, XCircle, Users, Warning, Calendar, Info } from "@phosphor-icons/react";
import { useYearPicker, useDatePicker, SUB_STATUS_TONE, WEEKDAY_LABELS } from "./_shared";

export default function ProxyDashboardPage() {
  const { years, yearId, setYearId } = useYearPicker();
  const { date, setDate } = useDatePicker();
  const [absences, setAbsences] = useState([]);
  const [loading, setLoading] = useState(false);
  const [picking, setPicking] = useState(null);  // { teacher, slot, candidates }
  const [subs, setSubs] = useState([]);

  const load = async () => {
    if (!yearId || !date) return;
    try {
      setLoading(true);
      const [{ data: absData }, { data: subData }] = await Promise.all([
        api.get("/school/proxy/absences", { params: { date, academic_year_id: yearId } }),
        api.get("/school/proxy/substitutions", { params: { date } }),
      ]);
      setAbsences(absData.absences || []);
      setSubs(subData || []);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [yearId, date]);

  const openPicker = async (abs, affected) => {
    try {
      const { data } = await api.get("/school/proxy/recommendations", {
        params: {
          date, academic_year_id: yearId,
          teacher_user_id: abs.teacher_user_id,
          section_id: affected.slot.section_id,
          period_no: affected.slot.period_no,
        },
      });
      const first = data.affected?.[0];
      setPicking({ teacher: abs.teacher, slot: affected.slot, candidates: first?.candidates || [] });
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const create = async (teacherUserId, autoApprove) => {
    try {
      await api.post("/school/proxy/substitutions", {
        date, academic_year_id: yearId,
        timetable_slot_id: picking.slot.id,
        substitute_teacher_user_id: teacherUserId,
        source: picking.teacher?.id ? "leave" : "manual",
        auto_approve: autoApprove,
      });
      toast.success(autoApprove ? "Assigned & approved" : "Substitution requested");
      setPicking(null); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const decide = async (id, action) => {
    try {
      await api.post(`/school/proxy/substitutions/${id}/${action}`, {});
      toast.success(action === "approve" ? "Approved" : action === "reject" ? "Rejected" : "Cancelled");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="space-y-6" data-testid="proxy-dashboard-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="overline text-[10px]">Timetable</div>
          <h1 className="font-heading text-3xl font-black" data-testid="proxy-page-title">Substitutes & Proxies</h1>
          <div className="text-xs text-[var(--tinted-grey-500)]">Spot absences, pick the best substitute, approve the override — the master timetable stays untouched.</div>
        </div>
        <div className="flex gap-2">
          <Link to="/school/timetable" className="text-xs underline" data-testid="link-to-grid">← Master Grid</Link>
          <Link to="/school/timetable/proxy-config" className="text-xs underline" data-testid="link-to-config">Settings →</Link>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-3">
        <div>
          <div className="overline text-[9px] mb-1">Academic year</div>
          <Select value={yearId} onValueChange={setYearId}>
            <SelectTrigger data-testid="proxy-year-picker"><SelectValue placeholder="Pick year" /></SelectTrigger>
            <SelectContent>
              {years.map((y) => <SelectItem key={y.id} value={y.id}>{y.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div>
          <div className="overline text-[9px] mb-1">Date</div>
          <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} data-testid="proxy-date-picker" />
        </div>
        <div className="flex items-end">
          <Button variant="outline" onClick={load} data-testid="proxy-refresh">
            <ArrowClockwise size={14} className="mr-1" />Re-run detection
          </Button>
        </div>
      </div>

      {loading && <div className="text-xs text-[var(--tinted-grey-500)]">Scanning…</div>}

      {absences.length === 0 && !loading && (
        <div className="border border-dashed border-[var(--tinted-grey-200)] p-10 text-center" data-testid="proxy-no-absences">
          <div className="font-heading text-xl font-black mb-1">All teachers accounted for</div>
          <div className="text-xs text-[var(--tinted-grey-500)]">No approved leave or post-cutoff absence detected for {date}.</div>
        </div>
      )}

      {absences.map((a) => (
        <div key={a.teacher_user_id} className="border border-[var(--tinted-grey-200)] bg-white p-4 space-y-3" data-testid={`absent-${a.teacher_user_id}`}>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <div className="font-bold text-sm">{a.teacher?.name || a.teacher_user_id}</div>
              <div className="text-[10px] text-[var(--tinted-grey-500)]">{a.teacher?.email}</div>
            </div>
            <div className="flex items-center gap-2 text-[10px]">
              <Badge className={a.source === "leave" ? "bg-amber-100 text-amber-700" : "bg-[var(--tinted-grey-100)]"}>
                {a.source === "leave" ? "Approved leave" : "Attendance signal"}
              </Badge>
              {a.reason && <span className="text-[var(--tinted-grey-500)]">{a.reason}</span>}
            </div>
          </div>
          <div className="space-y-2">
            {(a.affected_periods || []).map((p, i) => (
              <div key={i} className="flex items-center justify-between gap-2 p-2 border border-[var(--tinted-grey-200)]" data-testid={`affected-${a.teacher_user_id}-${p.slot.period_no}`}>
                <div className="text-xs">
                  <div className="font-mono">P{p.slot.period_no} · {WEEKDAY_LABELS[p.slot.weekday]}</div>
                  <div className="text-[10px] text-[var(--tinted-grey-500)]">Section: {p.slot.section_id?.slice(-6)}</div>
                </div>
                <div className="flex items-center gap-2">
                  {p.substitution ? (
                    <>
                      <Badge className={SUB_STATUS_TONE[p.substitution.status]}>{p.substitution.status}</Badge>
                      {p.substitution.status === "pending" && (
                        <>
                          <Button size="sm" onClick={() => decide(p.substitution.id, "approve")} data-testid={`sub-approve-${p.substitution.id}`}>
                            <CheckCircle size={12} className="mr-1" />Approve
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => decide(p.substitution.id, "reject")} data-testid={`sub-reject-${p.substitution.id}`}>
                            <XCircle size={12} className="mr-1" />Reject
                          </Button>
                        </>
                      )}
                      {p.substitution.status === "approved" && (
                        <Button size="sm" variant="outline" onClick={() => decide(p.substitution.id, "cancel")} data-testid={`sub-cancel-${p.substitution.id}`}>Cancel</Button>
                      )}
                    </>
                  ) : (
                    <Button size="sm" onClick={() => openPicker(a, p)} data-testid={`find-sub-${a.teacher_user_id}-${p.slot.period_no}`}>
                      <UserSwitch size={12} className="mr-1" />Find substitute
                    </Button>
                  )}
                </div>
              </div>
            ))}
            {(a.affected_periods || []).length === 0 && (
              <div className="text-[10px] text-[var(--tinted-grey-500)] italic">No periods scheduled on this weekday.</div>
            )}
          </div>
        </div>
      ))}

      {/* All substitutions table */}
      {subs.length > 0 && (
        <div>
          <h2 className="font-heading text-lg font-black mb-2 flex items-center gap-2"><Calendar size={16} />Substitutions for {date}</h2>
          <div className="border border-[var(--tinted-grey-200)] bg-white overflow-x-auto" data-testid="subs-table">
            <table className="min-w-full text-xs">
              <thead className="bg-[var(--tinted-grey-100)]">
                <tr>
                  <th className="p-2 text-left">Period</th>
                  <th className="p-2 text-left">Section</th>
                  <th className="p-2 text-left">Original</th>
                  <th className="p-2 text-left">Substitute</th>
                  <th className="p-2 text-left">Source</th>
                  <th className="p-2 text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                {subs.map((s) => (
                  <tr key={s.id} className="border-t border-[var(--tinted-grey-200)]" data-testid={`sub-row-${s.id}`}>
                    <td className="p-2 font-mono">P{s.period_no}</td>
                    <td className="p-2 font-mono">{s.section_id?.slice(-6)}</td>
                    <td className="p-2 font-mono">{s.original_teacher_user_id?.slice(-6)}</td>
                    <td className="p-2 font-mono">{s.substitute_teacher_user_id?.slice(-6)}</td>
                    <td className="p-2">{s.source}</td>
                    <td className="p-2"><Badge className={SUB_STATUS_TONE[s.status]}>{s.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {picking && (
        <CandidatePicker state={picking} onClose={() => setPicking(null)} onPick={create} />
      )}
    </div>
  );
}


function CandidatePicker({ state, onClose, onPick }) {
  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-2xl" data-testid="candidate-picker-dialog">
        <DialogHeader>
          <DialogTitle>Substitutes for {state.teacher?.name || "absent teacher"} · P{state.slot.period_no}</DialogTitle>
        </DialogHeader>
        <div className="space-y-2 max-h-[60vh] overflow-y-auto">
          {state.candidates.length === 0 && (
            <div className="text-xs text-[var(--tinted-grey-500)] py-4" data-testid="no-candidates">
              <Warning size={14} className="inline mr-1" />No eligible substitutes available for this period.
            </div>
          )}
          {state.candidates.map((c, i) => (
            <div key={c.teacher_user_id} className="border border-[var(--tinted-grey-200)] p-3 flex items-center justify-between gap-3 flex-wrap" data-testid={`candidate-${c.teacher_user_id}`}>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm">{c.name}</span>
                  {i === 0 && <Badge className="bg-[var(--klein)] text-white text-[10px]">Top pick</Badge>}
                </div>
                <div className="text-[10px] text-[var(--tinted-grey-500)]">{c.email}</div>
                <div className="flex gap-1 flex-wrap mt-1 text-[10px]">
                  {c.subject_match && <Badge className="bg-emerald-100 text-emerald-700">Subject match</Badge>}
                  {c.same_grade && <Badge className="bg-[var(--tinted-grey-100)]">Same grade</Badge>}
                  <Badge className="bg-[var(--tinted-grey-100)]">Load today: {c.daily_load}+{c.proxy_load}</Badge>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-mono font-black" data-testid={`candidate-score-${c.teacher_user_id}`}>{c.rank_score}</div>
                <div className="text-[9px] text-[var(--tinted-grey-500)]">rank score</div>
              </div>
              <div className="basis-full text-[10px] text-[var(--tinted-grey-500)]">
                {c.criteria.filter((cr) => cr.delta !== 0 || !cr.hit).map((cr) => (
                  <span key={cr.code} className="mr-2">
                    <Info size={10} className="inline mr-0.5" />{cr.label}{cr.delta ? ` (${cr.delta > 0 ? "+" : ""}${cr.delta})` : ""}
                  </span>
                ))}
              </div>
              <div className="flex gap-2 w-full justify-end">
                <Button size="sm" variant="outline" onClick={() => onPick(c.teacher_user_id, false)} data-testid={`pick-req-${c.teacher_user_id}`}>Request</Button>
                <Button size="sm" onClick={() => onPick(c.teacher_user_id, true)} data-testid={`pick-approve-${c.teacher_user_id}`}>Assign & approve</Button>
              </div>
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
