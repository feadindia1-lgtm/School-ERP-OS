import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { QrCode, Scan, CheckCircle, Warning } from "@phosphor-icons/react";
import { STATUS_TONE } from "./_shared";

export default function StudentScannerPage() {
  const [token, setToken] = useState("");
  const [sessionType, setSessionType] = useState("entry");
  const [recent, setRecent] = useState([]);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const t = token.trim();
    if (!t) return;
    setBusy(true);
    try {
      const { data } = await api.post("/school/attendance/students/scan", { token: t, session_type: sessionType });
      setRecent([{ ok: true, ...data, at: new Date().toLocaleTimeString() }, ...recent].slice(0, 20));
      toast.success(`${data.student.name} · ${data.daily.status}`);
      setToken("");
    } catch (e) {
      const code = e?.response?.data?.error?.details?.code || e?.response?.data?.detail?.code || "error";
      setRecent([{ ok: false, code, message: formatApiError(e), token: t.slice(0, 10) + "…", at: new Date().toLocaleTimeString() }, ...recent].slice(0, 20));
      toast.error(formatApiError(e));
    } finally { setBusy(false); }
  };

  return (
    <div data-testid="student-scanner-page">
      <div className="overline mb-2">Attendance</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="scanner-title">Gate scanner</h1>
      <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Scan a student QR card (webcam/handheld) or type the opaque code</div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white border border-[var(--tinted-grey-200)] p-5 lg:col-span-2" data-testid="scanner-input">
          <div className="flex items-center gap-3">
            <Select value={sessionType} onValueChange={setSessionType}>
              <SelectTrigger className="rounded-none h-11 w-[130px]" data-testid="scan-type"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="entry">Entry</SelectItem>
                <SelectItem value="exit">Exit</SelectItem>
              </SelectContent>
            </Select>
            <div className="relative flex-1">
              <QrCode size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tinted-grey-400)]" />
              <Input autoFocus value={token} onChange={e => setToken(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") submit(); }}
                placeholder="Scan or paste QR token"
                className="pl-9 h-11 rounded-none border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)] font-mono"
                data-testid="scan-input" />
            </div>
            <Button onClick={submit} disabled={busy || !token.trim()} data-testid="btn-scan-submit" className="rounded-full bg-[var(--klein)] text-white"><Scan size={14} className="mr-1"/> Scan</Button>
          </div>
          <div className="mt-6 overline">Recent scans ({recent.length})</div>
          <div className="mt-2 divide-y divide-[var(--tinted-grey-200)]" data-testid="scan-recent">
            {recent.length === 0 && <div className="py-4 text-sm text-[var(--tinted-grey-500)]">No scans yet.</div>}
            {recent.map((r, i) => (
              <div key={i} className={`py-2 flex items-center justify-between ${r.ok ? "" : "bg-[var(--accent-red)]/5"}`} data-testid={`scan-row-${i}`}>
                <div className="flex items-center gap-3">
                  {r.ok ? <CheckCircle size={16} className="text-[var(--klein)]"/> : <Warning size={16} className="text-[var(--accent-red)]"/>}
                  <div>
                    <div className="font-heading font-semibold text-sm">{r.ok ? r.student.name : r.message}</div>
                    <div className="text-xs text-[var(--tinted-grey-500)]">
                      {r.ok ? `${r.student.class_name || "—"} · ${r.daily.status} · ${r.at}` : `${r.code} · ${r.at}`}
                    </div>
                  </div>
                </div>
                {r.ok && <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${STATUS_TONE[r.daily.status] || ""}`}>{r.daily.status.replace("_"," ")}</span>}
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="scanner-tips">
          <div className="overline mb-3">Tips</div>
          <ul className="text-sm space-y-2 text-[var(--tinted-grey-500)]">
            <li>• Tokens are opaque; a lost card can be revoked without exposing student data.</li>
            <li>• Duplicate scans within the configured window are rejected — the student must wait before re-scanning.</li>
            <li>• Revoked / rotated tokens stop authenticating immediately.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
