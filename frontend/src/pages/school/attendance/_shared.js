/** Shared helpers / constants for Attendance pages. */
export const ATTENDANCE_STATUS = ["present", "absent", "late", "half_day", "excused", "holiday", "weekly_off", "on_leave"];
export const STATUS_TONE = {
  present: "bg-[var(--klein)] text-white",
  late: "bg-[var(--accent-yellow)] text-[var(--ink)]",
  half_day: "bg-[var(--accent-yellow)] text-[var(--ink)]",
  absent: "bg-[var(--accent-red)] text-white",
  excused: "bg-[var(--tinted-grey-500)] text-white",
  holiday: "bg-[var(--tinted-grey-300)] text-[var(--ink)]",
  weekly_off: "bg-[var(--tinted-grey-200)] text-[var(--ink)]",
  on_leave: "bg-[var(--tinted-grey-300)] text-[var(--ink)]",
  NOT_VERIFIED: "bg-[var(--tinted-grey-100)] text-[var(--tinted-grey-500)]",
  PENDING_REVIEW: "bg-[var(--accent-yellow)] text-[var(--ink)]",
  VERIFIED: "bg-[var(--klein)] text-white",
  REJECTED: "bg-[var(--accent-red)] text-white",
};

export async function captureSelfie(videoRef, canvasRef) {
  const video = videoRef.current;
  const canvas = canvasRef.current;
  if (!video || !canvas) throw new Error("Camera not initialised");
  canvas.width = video.videoWidth; canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return await new Promise((resolve) => canvas.toBlob(b => resolve(b), "image/jpeg", 0.85));
}

export function getGeolocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error("Geolocation unavailable on this device"));
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude, accuracy: p.coords.accuracy }),
      (err) => reject(err), { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  });
}
