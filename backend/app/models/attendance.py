"""Attendance Engine — Prompt 6.

Daily attendance plus entry/exit session records for both Staff and
Students.  Period-wise granularity is deliberately deferred to Prompt 7
Timetable, but the model is kept extensible via the optional
``period_no`` / ``timetable_slot_id`` placeholders on the session doc.
"""
from pydantic import Field

from app.models.base import BaseDocument


ATTENDANCE_STATUS = ["present", "absent", "late", "half_day", "excused", "holiday", "weekly_off", "on_leave"]
STUDENT_SESSION_TYPES = ["entry", "exit", "class", "manual"]
STAFF_SESSION_TYPES = ["clock_in", "clock_out", "manual"]
VERIFICATION_STATUS = ["NOT_VERIFIED", "PENDING_REVIEW", "VERIFIED", "REJECTED"]
CORRECTION_STATUS = ["pending", "approved", "rejected", "cancelled"]
QR_TOKEN_STATUS = ["active", "revoked", "rotated"]


class AttendanceConfig(BaseDocument):
    """One doc per tenant — editable by school_admin.

    Geofence coords are stored as decimal degrees.  `geofence_radius_m`
    plus `max_gps_accuracy_m` are the two numbers that gate every staff
    clock-in attempt.
    """
    tenant_id: str

    # Geofence
    geofence_lat: float | None = None
    geofence_lng: float | None = None
    geofence_radius_m: int = 150
    max_gps_accuracy_m: int = 50       # reject if device-reported accuracy worse than this
    allow_off_campus_with_approval: bool = True

    # Time rules
    workday_start: str = "09:00"       # HH:MM 24h
    workday_end: str = "16:00"
    late_threshold_minutes: int = 15   # minutes past workday_start that still counts as 'late'
    half_day_threshold_minutes: int = 240  # minutes present under threshold = half_day

    # QR / scanning
    qr_rotation_policy: str = "static_revocable"  # static_revocable | daily | hourly
    duplicate_scan_window_seconds: int = 60

    # Face verification
    face_verification_required: bool = True
    face_verification_provider: str = "none"      # none | aws_rekognition | fal_face_match | …
    face_verification_threshold: float = 0.75     # future providers compare score against this

    notes: str | None = None


# ---------- Staff attendance ----------
class StaffAttendance(BaseDocument):
    """One row per employee per date — session detail lives in StaffAttendanceSession."""
    tenant_id: str
    employee_id: str
    date: str                               # ISO date YYYY-MM-DD
    status: str = "absent"                  # ATTENDANCE_STATUS
    total_minutes: int = 0
    first_in_at: str | None = None
    last_out_at: str | None = None
    is_half_day: bool = False
    is_late: bool = False
    is_off_campus: bool = False
    off_campus_exception_id: str | None = None
    override_notes: str | None = None       # if manually overridden
    overridden_by_user_id: str | None = None
    overridden_at: str | None = None


class StaffAttendanceSession(BaseDocument):
    """One row per clock-in/clock-out/manual event for a staff member."""
    tenant_id: str
    employee_id: str
    date: str
    session_type: str = "clock_in"          # STAFF_SESSION_TYPES
    occurred_at: str                        # ISO datetime

    # Geofence
    device_lat: float | None = None
    device_lng: float | None = None
    device_accuracy_m: float | None = None
    distance_from_school_m: float | None = None
    inside_geofence: bool = False
    off_campus_exception_id: str | None = None

    # Face verification evidence
    face_storage_key: str | None = None     # pointer to storage service, NOT base64
    face_match_score: float | None = None   # populated by future provider
    verification_provider: str = "none"
    verification_reference: str | None = None  # provider's job id / request id
    verification_status: str = "NOT_VERIFIED"  # VERIFICATION_STATUS

    # Manual
    override_reason: str | None = None
    recorded_by_user_id: str | None = None
    notes: str | None = None


class OffCampusException(BaseDocument):
    """Pre-approval for off-campus attendance (field visits, home-tutoring, etc)."""
    tenant_id: str
    employee_id: str
    start_date: str
    end_date: str
    reason: str
    status: str = "pending"                 # pending | approved | rejected
    approved_by_user_id: str | None = None
    decision_at: str | None = None
    decision_reason: str | None = None
    requested_by_user_id: str | None = None


# ---------- Student attendance ----------
class StudentQRToken(BaseDocument):
    """Opaque token issued to each student.  NEVER contains student PII.

    `token` is a URL-safe random 32-byte secret stored in plaintext here but
    only shared once at issuance (printed on ID card).  Lookup is by indexed
    token; `status=revoked` immediately disables the card.
    """
    tenant_id: str
    student_id: str
    token: str
    status: str = "active"                  # QR_TOKEN_STATUS
    issued_at: str
    revoked_at: str | None = None
    rotated_from_token_id: str | None = None


class StudentAttendance(BaseDocument):
    tenant_id: str
    student_id: str
    date: str
    academic_year_id: str | None = None
    class_id: str | None = None
    section_id: str | None = None
    status: str = "absent"                  # ATTENDANCE_STATUS
    is_late: bool = False
    first_in_at: str | None = None
    last_out_at: str | None = None
    marked_by_user_id: str | None = None
    source: str = "manual"                  # manual | qr_scan | bulk | correction
    notes: str | None = None


class StudentAttendanceSession(BaseDocument):
    """Entry/exit/class scan events."""
    tenant_id: str
    student_id: str
    date: str
    session_type: str = "entry"             # STUDENT_SESSION_TYPES
    occurred_at: str
    token_id: str | None = None             # QR token used (if scan)
    class_id: str | None = None             # when marked by class teacher
    section_id: str | None = None
    period_no: int | None = None            # placeholder for Prompt-7
    timetable_slot_id: str | None = None    # placeholder for Prompt-7
    scanned_by_user_id: str | None = None
    status: str = "present"                 # see ATTENDANCE_STATUS
    notes: str | None = None


# ---------- Correction ----------
class AttendanceCorrection(BaseDocument):
    """Formal request → approval → applied; preserves old/new values."""
    tenant_id: str
    subject_kind: str = "student"           # student | staff
    subject_id: str                         # student_id or employee_id
    attendance_id: str                      # points at StudentAttendance / StaffAttendance
    date: str

    # Requested change
    old_status: str | None = None
    new_status: str
    old_notes: str | None = None
    new_notes: str | None = None

    reason: str
    status: str = "pending"                 # CORRECTION_STATUS
    requested_by_user_id: str | None = None
    approver_user_id: str | None = None
    decision_at: str | None = None
    decision_reason: str | None = None
    applied_at: str | None = None
