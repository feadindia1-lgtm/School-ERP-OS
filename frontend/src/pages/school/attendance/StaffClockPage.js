import { useEffect, useRef, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MapPin, Camera, Clock, Warning, CheckCircle } from "@phosphor-icons/react";
import { captureSelfie, getGeolocation, STATUS_TONE } from "./_shared";

const steps = [
  { key: "gps", label: "GPS lock", icon: MapPin },
  { key: "geo", label: "Geofence", icon: MapPin },
  { key: "face", label: "Face evidence", icon: Camera },
];

export default function StaffClockPage() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [sessionType, setSessionType] = useState("clock_in");
  const [coords, setCoords] = useState(null);
  const [status, setStatus] = useState({});   // { gps: 'ok'|'fail', geo: 'ok'|'fail', face: ... }
  const [messages, setMessages] = useState({});
  const [lastSession, setLastSession] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { (async () => {
    try { const { data } = await api.get("/school/attendance/config"); setCfg(data); }
    catch (e) { toast.error(formatApiError(e)); }
  })(); return () => { if (stream) stream.getTracks().forEach(t => t.stop()); }; /* eslint-disable-next-line */ }, []);

  const startCamera = async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
      setStream(s); if (videoRef.current) videoRef.current.srcObject = s;
    } catch (e) { setMessages(m => ({ ...m, face: "Camera permission denied" })); toast.error("Camera permission denied"); }
  };

  const grabGPS = async () => {
    try {
      const c = await getGeolocation(); setCoords(c);
      const threshold = cfg?.max_gps_accuracy_m ?? 50;
      if (c.accuracy > threshold) {
        setStatus(s => ({ ...s, gps: "fail" }));
        setMessages(m => ({ ...m, gps: `Accuracy ${Math.round(c.accuracy)}m worse than ${threshold}m threshold` }));
      } else {
        setStatus(s => ({ ...s, gps: "ok" }));
        setMessages(m => ({ ...m, gps: `±${Math.round(c.accuracy)}m` }));
      }
    } catch (e) { setStatus(s => ({ ...s, gps: "fail" })); setMessages(m => ({ ...m, gps: e.message || "GPS unavailable" })); }
  };

  const submit = async () => {
    if (!coords) return toast.error("Capture GPS first");
    setBusy(true);
    try {
      let blob = null;
      if (stream) blob = await captureSelfie(videoRef, canvasRef);
      const fd = new FormData();
      fd.append("session_type", sessionType);
      fd.append("device_lat", String(coords.lat));
      fd.append("device_lng", String(coords.lng));
      fd.append("device_accuracy_m", String(coords.accuracy));
      if (blob) fd.append("selfie", blob, "selfie.jpg");
      const { data } = await api.post("/school/attendance/staff/clock", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setLastSession(data);
      setStatus(s => ({ ...s, geo: "ok", face: data.session.verification_status }));
      setMessages(m => ({ ...m, geo: data.session.inside_geofence ? "Inside geofence" : "Off-campus (exception used)",
                               face: `Status: ${data.session.verification_status}` }));
      toast.success(`${sessionType === "clock_in" ? "Clocked in" : sessionType === "clock_out" ? "Clocked out" : "Recorded"} — daily ${data.daily.status}`);
    } catch (e) {
      const code = e?.response?.data?.error?.details?.code || e?.response?.data?.detail?.code;
      if (code === "outside_geofence") setStatus(s => ({ ...s, geo: "fail" })) & setMessages(m => ({ ...m, geo: e?.response?.data?.detail?.message || "Outside geofence" }));
      if (code === "gps_accuracy_too_low") setStatus(s => ({ ...s, gps: "fail" }));
      if (code === "face_evidence_required") setStatus(s => ({ ...s, face: "fail" })) & setMessages(m => ({ ...m, face: "Selfie required" }));
      toast.error(formatApiError(e));
    } finally { setBusy(false); }
  };

  return (
    <div data-testid="staff-clock-page">
      <div className="overline mb-2">Attendance</div>
      <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="clock-title">Clock in / out</h1>
      <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">Geofence → GPS → face evidence · evidence stored securely, never verified without a provider</div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white border border-[var(--tinted-grey-200)] p-5 lg:col-span-2" data-testid="clock-form">
          <div className="flex items-center gap-3 mb-4">
            <Select value={sessionType} onValueChange={setSessionType}>
              <SelectTrigger className="rounded-none h-10 w-[160px]" data-testid="clock-type"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="clock_in">Clock in</SelectItem>
                <SelectItem value="clock_out">Clock out</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={grabGPS} data-testid="btn-gps" className="rounded-full bg-[var(--ink)] hover:bg-[var(--klein)] text-white"><MapPin size={14} className="mr-1"/> Capture GPS</Button>
            <Button onClick={startCamera} data-testid="btn-start-camera" variant="outline" className="rounded-none"><Camera size={14} className="mr-1"/> Start camera</Button>
            <Button onClick={submit} disabled={busy || !coords} data-testid="btn-submit-clock" className="rounded-full bg-[var(--klein)] text-white"><Clock size={14} className="mr-1"/> {busy ? "Submitting…" : "Submit"}</Button>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {steps.map(s => {
              const Icon = s.icon;
              const val = status[s.key];
              const tone = val === "ok" || val === "VERIFIED" ? "bg-[var(--klein)] text-white" : val === "fail" || val === "REJECTED" ? "bg-[var(--accent-red)] text-white" : val ? "bg-[var(--accent-yellow)] text-[var(--ink)]" : "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]";
              return (
                <div key={s.key} className={`p-4 ${tone}`} data-testid={`step-${s.key}`}>
                  <div className="flex items-center gap-2"><Icon size={16} weight="duotone"/> <span className="overline text-[10px]">{s.label}</span></div>
                  <div className="mt-2 text-xs opacity-80">{messages[s.key] || (val || "pending")}</div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 bg-black">
            <video ref={videoRef} autoPlay playsInline muted className="w-full max-h-[300px] object-cover" data-testid="camera-video" />
            <canvas ref={canvasRef} className="hidden" />
          </div>
        </div>

        <div className="bg-white border border-[var(--tinted-grey-200)] p-5" data-testid="clock-sidepanel">
          <div className="overline mb-3">Policy</div>
          {cfg ? (
            <dl className="text-sm space-y-2">
              <div className="flex justify-between"><dt>Geofence radius</dt><dd className="font-mono">{cfg.geofence_radius_m}m</dd></div>
              <div className="flex justify-between"><dt>Max GPS accuracy</dt><dd className="font-mono">{cfg.max_gps_accuracy_m}m</dd></div>
              <div className="flex justify-between"><dt>Face required</dt><dd>{cfg.face_verification_required ? "Yes" : "No"}</dd></div>
              <div className="flex justify-between"><dt>Workday start</dt><dd className="font-mono">{cfg.workday_start}</dd></div>
              <div className="flex justify-between"><dt>Late threshold</dt><dd className="font-mono">{cfg.late_threshold_minutes}m</dd></div>
            </dl>
          ) : <div className="text-sm text-[var(--tinted-grey-500)]">Loading…</div>}
          {lastSession && (
            <div className="mt-4 pt-4 border-t border-[var(--tinted-grey-200)]" data-testid="last-session">
              <div className="overline mb-2">Last submission</div>
              <div className="flex items-center justify-between text-sm">
                <span>Daily status</span>
                <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${STATUS_TONE[lastSession.daily.status] || ""}`}>{lastSession.daily.status.replace("_"," ")}</span>
              </div>
              <div className="mt-1 flex items-center justify-between text-xs text-[var(--tinted-grey-500)]">
                <span>Verification</span>
                <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 ${STATUS_TONE[lastSession.session.verification_status] || ""}`}>{lastSession.session.verification_status}</span>
              </div>
              {lastSession.session.distance_from_school_m != null && (
                <div className="mt-1 flex items-center justify-between text-xs"><span>Distance</span><span className="font-mono">{Math.round(lastSession.session.distance_from_school_m)}m</span></div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
