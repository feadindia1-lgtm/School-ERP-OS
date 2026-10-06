import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Check, X, FloppyDisk, MapPin, Gear } from "@phosphor-icons/react";
import { STATUS_TONE } from "./_shared";

const tabTrig = "rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold";
const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export function AttendanceRegisterPage() {
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [staffRows, setStaffRows] = useState([]);
  const [studentRows, setStudentRows] = useState([]);
  const [overview, setOverview] = useState(null);

  const load = async () => {
    try {
      const [s, st, ov] = await Promise.all([
        api.get(`/school/attendance/staff?date=${date}`),
        api.get(`/school/attendance/students?date=${date}`),
        api.get(`/school/attendance/overview`),
      ]);
      setStaffRows(s.data); setStudentRows(st.data); setOverview(ov.data);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [date]);

  return (
    <div data-testid="register-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Attendance</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="register-title">Register</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Daily rollup for staff and students</div>
        </div>
        <Input type="date" value={date} onChange={e => setDate(e.target.value)} className="h-10 w-[180px] rounded-none" data-testid="register-date" />
      </div>

      {overview && (
        <div className="mt-6 grid grid-cols-2 lg:grid-cols-5 gap-3" data-testid="register-tiles">
          <Tile label="Staff present" value={overview.staff.present} tone="ink" />
          <Tile label="Staff absent" value={overview.staff.absent} tone="red" />
          <Tile label="Student present" value={overview.student.present} tone="klein" />
          <Tile label="Student absent" value={overview.student.absent} tone="red" />
          <Tile label="Pending corrections" value={overview.pending_corrections} tone="accent" />
        </div>
      )}

      <Tabs defaultValue="staff" className="mt-6">
        <TabsList className="rounded-none bg-transparent h-auto border-b border-[var(--tinted-grey-200)] w-full justify-start p-0">
          <TabsTrigger value="staff" className={tabTrig} data-testid="tab-staff">Staff ({staffRows.length})</TabsTrigger>
          <TabsTrigger value="students" className={tabTrig} data-testid="tab-students">Students ({studentRows.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="staff" className="mt-6">
          <div className="bg-white border border-[var(--tinted-grey-200)]">
            <Table data-testid="staff-register-table">
              <TableHeader><TableRow><TableHead>Employee</TableHead><TableHead>Status</TableHead><TableHead>First in</TableHead><TableHead>Last out</TableHead><TableHead>Mins</TableHead><TableHead>Flags</TableHead></TableRow></TableHeader>
              <TableBody>
                {staffRows.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="staff-register-empty">No staff records today.</TableCell></TableRow>}
                {staffRows.map(r => (
                  <TableRow key={r.id} data-testid={`staff-register-row-${r.id}`}>
                    <TableCell className="font-mono text-xs">{r.employee_id?.slice(0, 8)}…</TableCell>
                    <TableCell><span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${STATUS_TONE[r.status] || ""}`}>{r.status.replace("_"," ")}</span></TableCell>
                    <TableCell className="font-mono text-xs">{r.first_in_at ? r.first_in_at.slice(11, 16) : "—"}</TableCell>
                    <TableCell className="font-mono text-xs">{r.last_out_at ? r.last_out_at.slice(11, 16) : "—"}</TableCell>
                    <TableCell className="font-mono text-xs">{r.total_minutes}</TableCell>
                    <TableCell className="text-xs">
                      {r.is_late && <span className="mr-2 text-[var(--accent-yellow)]">late</span>}
                      {r.is_half_day && <span className="mr-2 text-[var(--accent-yellow)]">half</span>}
                      {r.is_off_campus && <span className="mr-2 text-[var(--klein)]">off-campus</span>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="students" className="mt-6">
          <div className="bg-white border border-[var(--tinted-grey-200)]">
            <Table data-testid="student-register-table">
              <TableHeader><TableRow><TableHead>Student</TableHead><TableHead>Status</TableHead><TableHead>Entry</TableHead><TableHead>Exit</TableHead><TableHead>Source</TableHead></TableRow></TableHeader>
              <TableBody>
                {studentRows.length === 0 && <TableRow><TableCell colSpan={5} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="student-register-empty">No student records today.</TableCell></TableRow>}
                {studentRows.map(r => (
                  <TableRow key={r.id} data-testid={`student-register-row-${r.id}`}>
                    <TableCell className="font-mono text-xs">{r.student_id?.slice(0, 8)}…</TableCell>
                    <TableCell><span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${STATUS_TONE[r.status] || ""}`}>{r.status.replace("_"," ")}</span></TableCell>
                    <TableCell className="font-mono text-xs">{r.first_in_at ? r.first_in_at.slice(11, 16) : "—"}</TableCell>
                    <TableCell className="font-mono text-xs">{r.last_out_at ? r.last_out_at.slice(11, 16) : "—"}</TableCell>
                    <TableCell className="text-xs capitalize">{r.source}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Tile({ label, value, tone }) {
  const toneClass = { ink: "bg-[var(--ink)] text-white", klein: "bg-[var(--klein)] text-white", red: "bg-[var(--accent-red)] text-white", accent: "bg-[var(--accent-yellow)] text-[var(--ink)]" };
  return (
    <div className={`p-4 ${toneClass[tone] || "bg-[var(--tinted-grey-100)]"}`}>
      <div className="overline text-[10px] opacity-80">{label}</div>
      <div className="mt-1 font-heading font-black text-3xl tracking-tighter tabular-nums">{value}</div>
    </div>
  );
}

export function CorrectionsPage() {
  const [status, setStatus] = useState("pending");
  const [items, setItems] = useState([]);

  const load = async () => {
    try { const { data } = await api.get(`/school/attendance/corrections?status=${status}`); setItems(data); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  const act = async (id, action) => {
    const reason = action !== "cancel" ? (window.prompt(`${action} reason?`) || "") : "";
    try { await api.post(`/school/attendance/corrections/${id}/${action}`, { reason }); toast.success(`Correction ${action}d`); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="corrections-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Attendance</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="corrections-title">Corrections</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Request → approval → applied · original value preserved</div>
        </div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="rounded-none h-10 w-[160px]" data-testid="corr-status-filter"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="mt-8 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="corrections-table">
          <TableHeader><TableRow><TableHead>Subject</TableHead><TableHead>Date</TableHead><TableHead>Old → New</TableHead><TableHead>Reason</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {items.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="corr-empty">No corrections in this view.</TableCell></TableRow>}
            {items.map(c => (
              <TableRow key={c.id} data-testid={`corr-row-${c.id}`}>
                <TableCell className="capitalize">{c.subject_kind} · <span className="font-mono text-xs">{c.subject_id?.slice(0, 8)}…</span></TableCell>
                <TableCell className="font-mono text-xs">{c.date}</TableCell>
                <TableCell className="text-xs">{c.old_status || "—"} → <strong>{c.new_status}</strong></TableCell>
                <TableCell className="text-xs">{c.reason}</TableCell>
                <TableCell><span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${STATUS_TONE[c.status] || "bg-[var(--tinted-grey-100)]"}`}>{c.status}</span></TableCell>
                <TableCell className="text-right space-x-1">
                  {c.status === "pending" && <>
                    <Button size="sm" variant="outline" onClick={() => act(c.id, "approve")} data-testid={`corr-approve-${c.id}`} className="rounded-none"><Check size={12}/></Button>
                    <Button size="sm" variant="outline" onClick={() => act(c.id, "reject")} data-testid={`corr-reject-${c.id}`} className="rounded-none text-[var(--accent-red)]"><X size={12}/></Button>
                    <Button size="sm" variant="outline" onClick={() => act(c.id, "cancel")} data-testid={`corr-cancel-${c.id}`} className="rounded-none">Cancel</Button>
                  </>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export function AttendanceConfigPage() {
  const [cfg, setCfg] = useState(null);
  useEffect(() => { (async () => {
    try { const { data } = await api.get("/school/attendance/config"); setCfg(data); }
    catch (e) { toast.error(formatApiError(e)); }
  })(); }, []);
  const save = async () => {
    try {
      await api.put("/school/attendance/config", {
        geofence_lat: cfg.geofence_lat, geofence_lng: cfg.geofence_lng,
        geofence_radius_m: Number(cfg.geofence_radius_m), max_gps_accuracy_m: Number(cfg.max_gps_accuracy_m),
        workday_start: cfg.workday_start, workday_end: cfg.workday_end,
        late_threshold_minutes: Number(cfg.late_threshold_minutes),
        half_day_threshold_minutes: Number(cfg.half_day_threshold_minutes),
        duplicate_scan_window_seconds: Number(cfg.duplicate_scan_window_seconds),
        face_verification_required: cfg.face_verification_required,
      });
      toast.success("Attendance config saved");
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const grab = async () => {
    if (!navigator.geolocation) return toast.error("Geolocation unavailable");
    navigator.geolocation.getCurrentPosition(p => setCfg(c => ({ ...c, geofence_lat: p.coords.latitude, geofence_lng: p.coords.longitude })), e => toast.error(e.message));
  };
  if (!cfg) return <div className="text-[var(--tinted-grey-500)]">Loading…</div>;
  return (
    <div data-testid="attendance-config-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Attendance</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="ac-title">Attendance config</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Geofence, GPS, time rules, QR + face policy</div>
        </div>
        <Button onClick={save} data-testid="btn-save-config" className="rounded-full bg-[var(--klein)] text-white"><FloppyDisk size={14} className="mr-1"/> Save</Button>
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="ac-geofence">
          <div className="overline mb-3">Geofence & GPS</div>
          <div className="grid grid-cols-2 gap-4">
            <div><Label className="overline">Latitude</Label><Input value={cfg.geofence_lat ?? ""} onChange={e => setCfg({ ...cfg, geofence_lat: e.target.value })} className={field} data-testid="ac-lat" /></div>
            <div><Label className="overline">Longitude</Label><Input value={cfg.geofence_lng ?? ""} onChange={e => setCfg({ ...cfg, geofence_lng: e.target.value })} className={field} data-testid="ac-lng" /></div>
            <div><Label className="overline">Radius (m)</Label><Input type="number" value={cfg.geofence_radius_m} onChange={e => setCfg({ ...cfg, geofence_radius_m: e.target.value })} className={field} data-testid="ac-radius" /></div>
            <div><Label className="overline">Max GPS acc (m)</Label><Input type="number" value={cfg.max_gps_accuracy_m} onChange={e => setCfg({ ...cfg, max_gps_accuracy_m: e.target.value })} className={field} data-testid="ac-acc" /></div>
            <div className="col-span-2"><Button variant="outline" onClick={grab} data-testid="btn-use-current-location" className="rounded-none"><MapPin size={12} className="mr-1"/> Use my current location</Button></div>
          </div>
        </div>
        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="ac-time">
          <div className="overline mb-3">Time & verification</div>
          <div className="grid grid-cols-2 gap-4">
            <div><Label className="overline">Workday start</Label><Input value={cfg.workday_start} onChange={e => setCfg({ ...cfg, workday_start: e.target.value })} placeholder="09:00" className={field} data-testid="ac-start" /></div>
            <div><Label className="overline">Workday end</Label><Input value={cfg.workday_end} onChange={e => setCfg({ ...cfg, workday_end: e.target.value })} placeholder="16:00" className={field} data-testid="ac-end" /></div>
            <div><Label className="overline">Late threshold (min)</Label><Input type="number" value={cfg.late_threshold_minutes} onChange={e => setCfg({ ...cfg, late_threshold_minutes: e.target.value })} className={field} data-testid="ac-late" /></div>
            <div><Label className="overline">Half-day under (min)</Label><Input type="number" value={cfg.half_day_threshold_minutes} onChange={e => setCfg({ ...cfg, half_day_threshold_minutes: e.target.value })} className={field} data-testid="ac-half" /></div>
            <div><Label className="overline">Duplicate scan window (s)</Label><Input type="number" value={cfg.duplicate_scan_window_seconds} onChange={e => setCfg({ ...cfg, duplicate_scan_window_seconds: e.target.value })} className={field} data-testid="ac-dup" /></div>
            <label className="flex items-center gap-2 text-sm mt-2 col-span-2">
              <input type="checkbox" checked={!!cfg.face_verification_required} onChange={e => setCfg({ ...cfg, face_verification_required: e.target.checked })} data-testid="ac-face-req" /> Require face selfie evidence
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
