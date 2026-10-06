"""Attendance Engine routes — Prompt 6.

Routes
------
Config:
  GET/PUT  /school/attendance/config

Staff:
  POST     /school/attendance/staff/clock      (3-layer: geofence → GPS → face evidence)
  GET      /school/attendance/staff            (daily register, filters)
  GET      /school/attendance/staff/summary    (monthly rollup)
  GET      /school/attendance/staff/{eid}      (one employee's day/month)
  POST     /school/attendance/staff/off-campus (request)
  POST     /school/attendance/staff/off-campus/{id}/approve
  POST     /school/attendance/staff/off-campus/{id}/reject

Student:
  POST     /school/attendance/students/qr-tokens          (issue/rotate)
  POST     /school/attendance/students/qr-tokens/{id}/revoke
  GET      /school/attendance/students/qr-tokens          (list)
  POST     /school/attendance/students/scan               (gate scan with opaque token)
  POST     /school/attendance/students/mark-class         (teacher bulk mark)
  GET      /school/attendance/students                    (daily/monthly report)
  GET      /school/attendance/students/{sid}/summary

Corrections:
  POST     /school/attendance/corrections                 (request)
  POST     /school/attendance/corrections/{id}/approve
  POST     /school/attendance/corrections/{id}/reject
  POST     /school/attendance/corrections/{id}/cancel
  GET      /school/attendance/corrections                 (inbox)

Overview:
  GET      /school/attendance/overview                    (dashboard counts)
"""
import math
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.core.deps import require_permission
from app.core.permissions import (
    P_ATTENDANCE_CONFIG, P_ATTENDANCE_CORRECTION_APPROVE,
    P_ATTENDANCE_CORRECTION_REQUEST, P_ATTENDANCE_VIEW,
    P_OFF_CAMPUS_APPROVE, P_STAFF_ATTENDANCE_CLOCK,
    P_STAFF_ATTENDANCE_MANAGE, P_STAFF_ATTENDANCE_OVERRIDE_P6,
    P_STUDENT_ATTENDANCE_MANAGE, P_STUDENT_ATTENDANCE_MARK,
    P_STUDENT_QR_MANAGE,
)
from app.models.attendance import (
    ATTENDANCE_STATUS, AttendanceConfig, AttendanceCorrection,
    OffCampusException, StaffAttendance, StaffAttendanceSession,
    StudentAttendance, StudentAttendanceSession, StudentQRToken,
)
from app.services.audit_service import log_event
from app.services.face_verification import get_provider
from app.services.storage import storage

router = APIRouter(prefix="/school/attendance", tags=["attendance"])


# ============================================================
# Helpers
# ============================================================
def _oid(v: str) -> ObjectId:
    try: return ObjectId(v)
    except InvalidId: raise HTTPException(status_code=404, detail="Not found")


def _out(d: dict) -> dict:
    d = dict(d); d["id"] = str(d.pop("_id")); return d


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres."""
    R = 6371008.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def _get_config(db, tid: str) -> dict:
    cfg = await db.attendance_configs.find_one({"tenant_id": tid})
    if cfg: return cfg
    doc = AttendanceConfig(tenant_id=tid).to_mongo()
    res = await db.attendance_configs.insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


def _minutes_since(hhmm: str, dt_iso: str) -> int:
    """How many minutes past HH:MM is the given datetime (same date assumed)."""
    try:
        h, m = map(int, hhmm.split(":"))
        when = datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
        anchor = when.replace(hour=h, minute=m, second=0, microsecond=0)
        delta = when - anchor
        return int(delta.total_seconds() // 60)
    except Exception:
        return 0


# ============================================================
# Config
# ============================================================
class ConfigIn(BaseModel):
    geofence_lat: float | None = None
    geofence_lng: float | None = None
    geofence_radius_m: int | None = None
    max_gps_accuracy_m: int | None = None
    allow_off_campus_with_approval: bool | None = None
    workday_start: str | None = None
    workday_end: str | None = None
    late_threshold_minutes: int | None = None
    half_day_threshold_minutes: int | None = None
    qr_rotation_policy: str | None = None
    duplicate_scan_window_seconds: int | None = None
    face_verification_required: bool | None = None
    face_verification_provider: str | None = None
    face_verification_threshold: float | None = None
    notes: str | None = None


@router.get("/config")
async def get_config(user: dict = Depends(require_permission(P_ATTENDANCE_VIEW))):
    return _out(await _get_config(get_db(), user["tenant_id"]))


@router.put("/config")
async def update_config(payload: ConfigIn, request: Request, user: dict = Depends(require_permission(P_ATTENDANCE_CONFIG))):
    db = get_db()
    cfg = await _get_config(db, user["tenant_id"])
    updates = payload.model_dump(exclude_none=True)
    if updates.get("geofence_radius_m") is not None and updates["geofence_radius_m"] <= 0:
        raise HTTPException(status_code=400, detail="geofence_radius_m must be > 0")
    if updates.get("max_gps_accuracy_m") is not None and updates["max_gps_accuracy_m"] <= 0:
        raise HTTPException(status_code=400, detail="max_gps_accuracy_m must be > 0")
    updates["updated_at"] = _now()
    await db.attendance_configs.update_one({"_id": cfg["_id"]}, {"$set": updates})
    await log_event(action="attendance.config.update", resource="attendance_config",
                    resource_id=str(cfg["_id"]), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value=updates)
    return _out(await db.attendance_configs.find_one({"_id": cfg["_id"]}))


# ============================================================
# Staff clock-in (3-layer flow)
# ============================================================
async def _recompute_staff_day(db, cfg: dict, tid: str, employee_id: str, date: str) -> dict:
    """Aggregate sessions → derive status/total_minutes/half_day/late/first_in/last_out."""
    sessions = await db.staff_attendance_sessions.find({
        "tenant_id": tid, "employee_id": employee_id, "date": date,
    }).sort("occurred_at", 1).to_list(500)
    ins = [s for s in sessions if s["session_type"] in {"clock_in", "manual"}]
    outs = [s for s in sessions if s["session_type"] == "clock_out"]
    first_in = ins[0]["occurred_at"] if ins else None
    last_out = outs[-1]["occurred_at"] if outs else None
    total_minutes = 0
    if first_in:
        try:
            start = datetime.fromisoformat(first_in.replace("Z", "+00:00"))
            end = datetime.fromisoformat((last_out or _now()).replace("Z", "+00:00"))
            total_minutes = max(0, int((end - start).total_seconds() // 60))
        except Exception:
            total_minutes = 0
    status = "absent"
    is_late = False
    is_half_day = False
    if first_in:
        late_mins = _minutes_since(cfg.get("workday_start", "09:00"), first_in)
        is_late = late_mins > int(cfg.get("late_threshold_minutes") or 15)
        if total_minutes < int(cfg.get("half_day_threshold_minutes") or 240):
            is_half_day = True
            status = "half_day"
        else:
            status = "late" if is_late else "present"
    is_off_campus = any(not s.get("inside_geofence") for s in ins) if ins else False
    existing = await db.staff_attendance.find_one({"tenant_id": tid, "employee_id": employee_id, "date": date})
    update = {
        "status": status, "total_minutes": total_minutes,
        "first_in_at": first_in, "last_out_at": last_out,
        "is_half_day": is_half_day, "is_late": is_late,
        "is_off_campus": is_off_campus, "updated_at": _now(),
    }
    if existing:
        await db.staff_attendance.update_one({"_id": existing["_id"]}, {"$set": update})
        existing.update(update); return existing
    doc = StaffAttendance(tenant_id=tid, employee_id=employee_id, date=date, **update).to_mongo()
    res = await db.staff_attendance.insert_one(doc); doc["_id"] = res.inserted_id
    return doc


@router.post("/staff/clock")
async def staff_clock(
    request: Request,
    session_type: str = Form("clock_in"),
    device_lat: float = Form(...),
    device_lng: float = Form(...),
    device_accuracy_m: float = Form(...),
    employee_id: str | None = Form(None),
    off_campus_exception_id: str | None = Form(None),
    notes: str | None = Form(None),
    selfie: UploadFile | None = File(None),
    user: dict = Depends(require_permission(P_STAFF_ATTENDANCE_CLOCK)),
):
    """Three-layer staff attendance capture.

    Layer 1: GPS accuracy must be within tenant-configured threshold.
    Layer 2: Geofence distance (haversine) — if outside, requires an
    approved off-campus exception.
    Layer 3: Face evidence captured → stored via storage service →
    pluggable verifier returns status.  Never fabricates VERIFIED.
    """
    if session_type not in {"clock_in", "clock_out", "manual"}:
        raise HTTPException(status_code=400, detail=f"Invalid session_type: {session_type}")
    db = get_db()
    tid = user["tenant_id"]
    cfg = await _get_config(db, tid)

    # Resolve employee — self-serve if the user has a linked Employee.
    if not employee_id:
        if not user.get("employee_id"):
            u = await db.users.find_one({"_id": _oid(user["id"])})
            employee_id = (u or {}).get("employee_id")
        else:
            employee_id = user.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail={"code": "employee_unresolved", "message": "No linked Employee for this user. Admin must link via Staff → Employee → user_id."})
    emp = await db.employees.find_one({"_id": _oid(employee_id), "tenant_id": tid})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # ----- Layer 1: GPS accuracy -----
    if device_accuracy_m > float(cfg.get("max_gps_accuracy_m") or 50):
        raise HTTPException(status_code=400, detail={
            "code": "gps_accuracy_too_low",
            "message": f"GPS accuracy {device_accuracy_m}m worse than threshold {cfg.get('max_gps_accuracy_m')}m",
        })

    # ----- Layer 2: Geofence -----
    inside = False
    distance_m = None
    if cfg.get("geofence_lat") is not None and cfg.get("geofence_lng") is not None:
        distance_m = _haversine_m(cfg["geofence_lat"], cfg["geofence_lng"], device_lat, device_lng)
        inside = distance_m <= float(cfg.get("geofence_radius_m") or 150)
    else:
        # No geofence set — admins must set one.  Treat as inside for first-run.
        inside = True
    off_campus_ok = False
    if not inside:
        if off_campus_exception_id:
            exc = await db.off_campus_exceptions.find_one({
                "_id": _oid(off_campus_exception_id), "tenant_id": tid,
                "employee_id": employee_id, "status": "approved",
            })
            if not exc:
                raise HTTPException(status_code=403, detail={"code": "off_campus_exception_invalid", "message": "Exception missing or not approved"})
            today = _today_iso()
            if not (exc["start_date"] <= today <= exc["end_date"]):
                raise HTTPException(status_code=403, detail={"code": "off_campus_exception_expired", "message": "Approved exception doesn't cover today"})
            off_campus_ok = True
        else:
            raise HTTPException(status_code=403, detail={
                "code": "outside_geofence",
                "message": f"You are {int(distance_m or 0)}m away. Request an off-campus exception.",
                "distance_m": distance_m,
            })

    # ----- Layer 3: Face evidence -----
    face_storage_key = None
    verification_status = "NOT_VERIFIED"
    face_match_score = None
    verification_provider = cfg.get("face_verification_provider") or "none"
    verification_reference = None
    if selfie is not None:
        raw = await selfie.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Empty selfie upload")
        # Store via the storage abstraction — tenant-scoped, no base64 in Mongo.
        doc_id = f"face-{employee_id}-{_now().replace(':', '').replace('.', '')}"
        face_storage_key = await storage.put(tid, doc_id, raw)
        provider = get_provider(verification_provider)
        result = await provider.verify(
            tenant_id=tid, employee_id=employee_id, selfie_bytes=raw,
            reference_storage_key=emp.get("photo_url"),
        )
        verification_status = result.status
        face_match_score = result.match_score
        verification_reference = result.reference
    elif cfg.get("face_verification_required"):
        raise HTTPException(status_code=400, detail={
            "code": "face_evidence_required",
            "message": "A selfie is required by this school's attendance policy",
        })

    today = _today_iso()
    session = StaffAttendanceSession(
        tenant_id=tid, employee_id=employee_id, date=today,
        session_type=session_type, occurred_at=_now(),
        device_lat=device_lat, device_lng=device_lng,
        device_accuracy_m=device_accuracy_m, distance_from_school_m=distance_m,
        inside_geofence=inside,
        off_campus_exception_id=off_campus_exception_id if off_campus_ok else None,
        face_storage_key=face_storage_key, face_match_score=face_match_score,
        verification_provider=verification_provider,
        verification_reference=verification_reference,
        verification_status=verification_status,
        recorded_by_user_id=user["id"], notes=notes,
    ).to_mongo()
    res = await db.staff_attendance_sessions.insert_one(session); session["_id"] = res.inserted_id

    daily = await _recompute_staff_day(db, cfg, tid, employee_id, today)
    await log_event(action="attendance.staff.session", resource="staff_attendance_session",
                    resource_id=str(res.inserted_id), tenant_id=tid, actor=user, request=request,
                    metadata={"employee_id": employee_id, "session_type": session_type,
                              "inside_geofence": inside, "distance_m": distance_m,
                              "verification_status": verification_status})
    return {"session": _out(session), "daily": _out(daily)}


class StaffManualIn(BaseModel):
    employee_id: str
    date: str                   # YYYY-MM-DD
    status: str                 # ATTENDANCE_STATUS
    reason: str = Field(min_length=1, max_length=500)


@router.post("/staff/manual")
async def staff_manual_mark(payload: StaffManualIn, request: Request, user: dict = Depends(require_permission(P_STAFF_ATTENDANCE_OVERRIDE_P6))):
    """HR/Admin manual override — writes a daily record with override metadata."""
    if payload.status not in ATTENDANCE_STATUS:
        raise HTTPException(status_code=400, detail=f"Allowed status: {ATTENDANCE_STATUS}")
    db = get_db()
    tid = user["tenant_id"]
    if not await db.employees.find_one({"_id": _oid(payload.employee_id), "tenant_id": tid}):
        raise HTTPException(status_code=404, detail="Employee not found")
    existing = await db.staff_attendance.find_one({"tenant_id": tid, "employee_id": payload.employee_id, "date": payload.date})
    update = {
        "status": payload.status, "override_notes": payload.reason,
        "overridden_by_user_id": user["id"], "overridden_at": _now(),
        "updated_at": _now(),
    }
    if existing:
        await db.staff_attendance.update_one({"_id": existing["_id"]}, {"$set": update})
    else:
        doc = StaffAttendance(tenant_id=tid, employee_id=payload.employee_id, date=payload.date, **update).to_mongo()
        res = await db.staff_attendance.insert_one(doc)
    await log_event(action="attendance.staff.override", resource="staff_attendance",
                    resource_id=str(existing["_id"]) if existing else str(res.inserted_id),
                    tenant_id=tid, actor=user, request=request,
                    new_value={"status": payload.status}, metadata={"reason": payload.reason})
    return {"ok": True}


@router.get("/staff")
async def list_staff_attendance(
    date: str | None = None, from_date: str | None = None, to_date: str | None = None,
    employee_id: str | None = None, status: str | None = None,
    user: dict = Depends(require_permission(P_ATTENDANCE_VIEW)),
):
    q: dict = {"tenant_id": user["tenant_id"]}
    if date: q["date"] = date
    elif from_date or to_date:
        q["date"] = {}
        if from_date: q["date"]["$gte"] = from_date
        if to_date: q["date"]["$lte"] = to_date
    if employee_id: q["employee_id"] = employee_id
    if status: q["status"] = status
    docs = await get_db().staff_attendance.find(q).sort("date", -1).to_list(1000)
    return [_out(d) for d in docs]


@router.get("/staff/summary")
async def staff_summary(
    from_date: str, to_date: str, employee_id: str | None = None,
    user: dict = Depends(require_permission(P_ATTENDANCE_VIEW)),
):
    db = get_db()
    match: dict = {"tenant_id": user["tenant_id"], "date": {"$gte": from_date, "$lte": to_date}}
    if employee_id: match["employee_id"] = employee_id
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"employee_id": "$employee_id", "status": "$status"},
            "count": {"$sum": 1},
            "minutes": {"$sum": {"$ifNull": ["$total_minutes", 0]}},
        }},
    ]
    rows = await db.staff_attendance.aggregate(pipeline).to_list(5000)
    out: dict = {}
    for r in rows:
        eid = r["_id"]["employee_id"]
        out.setdefault(eid, {"employee_id": eid, "by_status": {}, "total_minutes": 0})
        out[eid]["by_status"][r["_id"]["status"]] = r["count"]
        out[eid]["total_minutes"] += r["minutes"]
    return list(out.values())


# ---- Off-campus exceptions ----
class OffCampusIn(BaseModel):
    employee_id: str
    start_date: str
    end_date: str
    reason: str = Field(min_length=1, max_length=500)


@router.post("/staff/off-campus", status_code=201)
async def request_off_campus(payload: OffCampusIn, request: Request, user: dict = Depends(require_permission(P_STAFF_ATTENDANCE_CLOCK))):
    db = get_db()
    if payload.start_date > payload.end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    if not await db.employees.find_one({"_id": _oid(payload.employee_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Employee not found")
    doc = OffCampusException(
        tenant_id=user["tenant_id"], employee_id=payload.employee_id,
        start_date=payload.start_date, end_date=payload.end_date,
        reason=payload.reason, requested_by_user_id=user["id"],
    ).to_mongo()
    res = await db.off_campus_exceptions.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="attendance.off_campus.request", resource="off_campus_exception",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, metadata={"employee_id": payload.employee_id})
    return _out(doc)


@router.get("/staff/off-campus")
async def list_off_campus(status: str | None = None, user: dict = Depends(require_permission(P_ATTENDANCE_VIEW))):
    q: dict = {"tenant_id": user["tenant_id"]}
    if status: q["status"] = status
    docs = await get_db().off_campus_exceptions.find(q).sort("created_at", -1).to_list(500)
    return [_out(d) for d in docs]


class DecisionIn(BaseModel):
    reason: str | None = None


@router.post("/staff/off-campus/{eid}/approve")
async def approve_off_campus(eid: str, payload: DecisionIn, request: Request, user: dict = Depends(require_permission(P_OFF_CAMPUS_APPROVE))):
    db = get_db()
    old = await db.off_campus_exceptions.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Exception not found")
    if old["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot approve — current status {old['status']}")
    await db.off_campus_exceptions.update_one({"_id": old["_id"]}, {"$set": {
        "status": "approved", "approved_by_user_id": user["id"],
        "decision_at": _now(), "decision_reason": payload.reason, "updated_at": _now(),
    }})
    await log_event(action="attendance.off_campus.approve", resource="off_campus_exception",
                    resource_id=eid, tenant_id=user["tenant_id"], actor=user, request=request)
    return _out(await db.off_campus_exceptions.find_one({"_id": old["_id"]}))


@router.post("/staff/off-campus/{eid}/reject")
async def reject_off_campus(eid: str, payload: DecisionIn, request: Request, user: dict = Depends(require_permission(P_OFF_CAMPUS_APPROVE))):
    db = get_db()
    old = await db.off_campus_exceptions.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Exception not found")
    if old["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot reject — current status {old['status']}")
    await db.off_campus_exceptions.update_one({"_id": old["_id"]}, {"$set": {
        "status": "rejected", "approved_by_user_id": user["id"],
        "decision_at": _now(), "decision_reason": payload.reason, "updated_at": _now(),
    }})
    return _out(await db.off_campus_exceptions.find_one({"_id": old["_id"]}))


# ============================================================
# Student QR tokens
# ============================================================
class IssueQRIn(BaseModel):
    student_id: str
    rotate: bool = False       # revoke existing active token, issue new one


@router.get("/students/qr-tokens")
async def list_qr_tokens(student_id: str | None = None, status: str | None = None, user: dict = Depends(require_permission(P_STUDENT_QR_MANAGE))):
    q: dict = {"tenant_id": user["tenant_id"]}
    if student_id: q["student_id"] = student_id
    if status: q["status"] = status
    docs = await get_db().student_qr_tokens.find(q).sort("created_at", -1).to_list(500)
    return [_out(d) for d in docs]


@router.post("/students/qr-tokens", status_code=201)
async def issue_qr_token(payload: IssueQRIn, request: Request, user: dict = Depends(require_permission(P_STUDENT_QR_MANAGE))):
    db = get_db()
    tid = user["tenant_id"]
    if not await db.students.find_one({"_id": _oid(payload.student_id), "tenant_id": tid}):
        raise HTTPException(status_code=404, detail="Student not found")
    prev = await db.student_qr_tokens.find_one({"tenant_id": tid, "student_id": payload.student_id, "status": "active"})
    if prev and not payload.rotate:
        raise HTTPException(status_code=409, detail={"code": "token_exists", "message": "Student already has an active token. Pass rotate=true to replace."})
    if prev and payload.rotate:
        await db.student_qr_tokens.update_one({"_id": prev["_id"]}, {"$set": {
            "status": "rotated", "revoked_at": _now(), "updated_at": _now(),
        }})
    token = secrets.token_urlsafe(24)
    doc = StudentQRToken(
        tenant_id=tid, student_id=payload.student_id, token=token,
        status="active", issued_at=_now(),
        rotated_from_token_id=str(prev["_id"]) if prev else None,
    ).to_mongo()
    res = await db.student_qr_tokens.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="attendance.qr.issue", resource="student_qr_token",
                    resource_id=str(res.inserted_id), tenant_id=tid, actor=user, request=request,
                    metadata={"student_id": payload.student_id, "rotated": bool(prev and payload.rotate)})
    return _out(doc)


@router.post("/students/qr-tokens/{tid}/revoke")
async def revoke_qr_token(tid: str, request: Request, user: dict = Depends(require_permission(P_STUDENT_QR_MANAGE))):
    db = get_db()
    old = await db.student_qr_tokens.find_one({"_id": _oid(tid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Token not found")
    if old["status"] != "active":
        raise HTTPException(status_code=409, detail=f"Token already {old['status']}")
    await db.student_qr_tokens.update_one({"_id": old["_id"]}, {"$set": {
        "status": "revoked", "revoked_at": _now(), "updated_at": _now(),
    }})
    await log_event(action="attendance.qr.revoke", resource="student_qr_token",
                    resource_id=tid, tenant_id=user["tenant_id"], actor=user, request=request)
    return _out(await db.student_qr_tokens.find_one({"_id": old["_id"]}))


# ============================================================
# Student scan + class mark + reports
# ============================================================
async def _recompute_student_day(db, cfg: dict, tid: str, student_id: str, date: str) -> dict:
    sessions = await db.student_attendance_sessions.find({
        "tenant_id": tid, "student_id": student_id, "date": date,
    }).sort("occurred_at", 1).to_list(500)
    ins = [s for s in sessions if s["session_type"] in {"entry", "class", "manual"}]
    outs = [s for s in sessions if s["session_type"] == "exit"]
    first_in = ins[0]["occurred_at"] if ins else None
    last_out = outs[-1]["occurred_at"] if outs else None
    status = "present" if first_in else "absent"
    is_late = False
    if first_in:
        is_late = _minutes_since(cfg.get("workday_start", "09:00"), first_in) > int(cfg.get("late_threshold_minutes") or 15)
        if is_late: status = "late"
    # Class mark takes precedence if a non-present status was explicitly set.
    explicit = [s for s in sessions if s["session_type"] == "class" and s.get("status") in ATTENDANCE_STATUS]
    if explicit:
        status = explicit[-1]["status"]
        is_late = status == "late"
    # Infer class/section from a class-mark session if present
    class_id = next((s.get("class_id") for s in sessions if s.get("class_id")), None)
    section_id = next((s.get("section_id") for s in sessions if s.get("section_id")), None)
    existing = await db.student_attendance.find_one({"tenant_id": tid, "student_id": student_id, "date": date})
    update = {
        "status": status, "is_late": is_late,
        "first_in_at": first_in, "last_out_at": last_out,
        "class_id": class_id, "section_id": section_id,
        "updated_at": _now(),
    }
    if existing:
        await db.student_attendance.update_one({"_id": existing["_id"]}, {"$set": update})
        existing.update(update); return existing
    doc = StudentAttendance(tenant_id=tid, student_id=student_id, date=date, source="qr_scan", **update).to_mongo()
    res = await db.student_attendance.insert_one(doc); doc["_id"] = res.inserted_id
    return doc


class ScanIn(BaseModel):
    token: str
    session_type: str = "entry"


@router.post("/students/scan")
async def student_scan(payload: ScanIn, request: Request, user: dict = Depends(require_permission(P_STUDENT_ATTENDANCE_MARK))):
    """Gate scanner — resolves opaque QR token, enforces revocation + duplicate-scan window."""
    if payload.session_type not in {"entry", "exit"}:
        raise HTTPException(status_code=400, detail="session_type must be entry|exit")
    db = get_db()
    tid = user["tenant_id"]
    cfg = await _get_config(db, tid)
    tok = await db.student_qr_tokens.find_one({"tenant_id": tid, "token": payload.token})
    if not tok:
        raise HTTPException(status_code=404, detail={"code": "token_not_found", "message": "QR token not recognised"})
    if tok["status"] != "active":
        raise HTTPException(status_code=403, detail={"code": "token_revoked", "message": f"Token is {tok['status']}"})
    student = await db.students.find_one({"_id": _oid(tok["student_id"]), "tenant_id": tid})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    # Duplicate-scan debounce
    today = _today_iso()
    window_s = int(cfg.get("duplicate_scan_window_seconds") or 60)
    recent = await db.student_attendance_sessions.find({
        "tenant_id": tid, "student_id": tok["student_id"], "date": today,
        "session_type": payload.session_type,
    }).sort("occurred_at", -1).limit(1).to_list(1)
    if recent:
        try:
            last_at = datetime.fromisoformat(recent[0]["occurred_at"].replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - last_at).total_seconds() < window_s:
                raise HTTPException(status_code=409, detail={
                    "code": "duplicate_scan",
                    "message": f"Duplicate {payload.session_type} scan within {window_s}s window",
                })
        except HTTPException: raise
        except Exception: pass
    session = StudentAttendanceSession(
        tenant_id=tid, student_id=tok["student_id"], date=today,
        session_type=payload.session_type, occurred_at=_now(),
        token_id=str(tok["_id"]), scanned_by_user_id=user["id"], status="present",
    ).to_mongo()
    res = await db.student_attendance_sessions.insert_one(session); session["_id"] = res.inserted_id
    daily = await _recompute_student_day(db, cfg, tid, tok["student_id"], today)
    await log_event(action="attendance.student.scan", resource="student_attendance_session",
                    resource_id=str(res.inserted_id), tenant_id=tid, actor=user, request=request,
                    metadata={"student_id": tok["student_id"], "session_type": payload.session_type})
    return {"session": _out(session), "daily": _out(daily),
            "student": {"id": str(student["_id"]), "name": f"{student.get('first_name','')} {student.get('last_name','')}".strip(),
                        "class_name": student.get("class_name"), "section": student.get("section")}}


class ClassMarkEntry(BaseModel):
    student_id: str
    status: str
    notes: str | None = None


class ClassMarkIn(BaseModel):
    date: str
    class_id: str
    section_id: str | None = None
    entries: list[ClassMarkEntry]


@router.post("/students/mark-class")
async def mark_class(payload: ClassMarkIn, request: Request, user: dict = Depends(require_permission(P_STUDENT_ATTENDANCE_MARK))):
    """Teacher bulk mark — writes a 'class' session per entry and rolls up the day."""
    if not payload.entries:
        raise HTTPException(status_code=400, detail="entries cannot be empty")
    db = get_db()
    tid = user["tenant_id"]
    cfg = await _get_config(db, tid)
    # Validate class/section existence
    if not await db.academic_classes.find_one({"_id": _oid(payload.class_id), "tenant_id": tid}):
        raise HTTPException(status_code=404, detail="Class not found")
    if payload.section_id and not await db.academic_sections.find_one({"_id": _oid(payload.section_id), "tenant_id": tid}):
        raise HTTPException(status_code=404, detail="Section not found")
    accepted, failed = [], []
    for e in payload.entries:
        if e.status not in ATTENDANCE_STATUS:
            failed.append({"student_id": e.student_id, "code": "invalid_status", "status": e.status})
            continue
        if not await db.students.find_one({"_id": _oid(e.student_id), "tenant_id": tid}):
            failed.append({"student_id": e.student_id, "code": "student_not_found"}); continue
        session = StudentAttendanceSession(
            tenant_id=tid, student_id=e.student_id, date=payload.date,
            session_type="class", occurred_at=_now(),
            class_id=payload.class_id, section_id=payload.section_id,
            scanned_by_user_id=user["id"], status=e.status, notes=e.notes,
        ).to_mongo()
        await db.student_attendance_sessions.insert_one(session)
        daily = await _recompute_student_day(db, cfg, tid, e.student_id, payload.date)
        await db.student_attendance.update_one({"_id": daily["_id"]}, {"$set": {
            "class_id": payload.class_id, "section_id": payload.section_id,
            "marked_by_user_id": user["id"], "source": "bulk",
        }})
        accepted.append(e.student_id)
    await log_event(action="attendance.student.bulk_mark", resource="student_attendance",
                    resource_id=payload.class_id, tenant_id=tid, actor=user, request=request,
                    metadata={"date": payload.date, "accepted": len(accepted), "failed": len(failed)})
    return {"accepted": accepted, "failed": failed, "total": len(payload.entries)}


@router.get("/students")
async def list_student_attendance(
    date: str | None = None, from_date: str | None = None, to_date: str | None = None,
    student_id: str | None = None, class_id: str | None = None, section_id: str | None = None,
    status: str | None = None,
    user: dict = Depends(require_permission(P_ATTENDANCE_VIEW)),
):
    q: dict = {"tenant_id": user["tenant_id"]}
    if date: q["date"] = date
    elif from_date or to_date:
        q["date"] = {}
        if from_date: q["date"]["$gte"] = from_date
        if to_date: q["date"]["$lte"] = to_date
    if student_id: q["student_id"] = student_id
    if class_id: q["class_id"] = class_id
    if section_id: q["section_id"] = section_id
    if status: q["status"] = status
    docs = await get_db().student_attendance.find(q).sort("date", -1).to_list(2000)
    return [_out(d) for d in docs]


@router.get("/students/{sid}/summary")
async def student_summary(sid: str, from_date: str, to_date: str, user: dict = Depends(require_permission(P_ATTENDANCE_VIEW))):
    db = get_db()
    tid = user["tenant_id"]
    if not await db.students.find_one({"_id": _oid(sid), "tenant_id": tid}):
        raise HTTPException(status_code=404, detail="Student not found")
    pipeline = [
        {"$match": {"tenant_id": tid, "student_id": sid, "date": {"$gte": from_date, "$lte": to_date}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    rows = await db.student_attendance.aggregate(pipeline).to_list(100)
    return {"student_id": sid, "from": from_date, "to": to_date,
            "by_status": {r["_id"]: r["count"] for r in rows}}


# ============================================================
# Corrections (formal request → approval → applied)
# ============================================================
class CorrectionIn(BaseModel):
    subject_kind: str                                    # "student" | "staff"
    subject_id: str
    date: str
    new_status: str
    reason: str = Field(min_length=1, max_length=500)
    new_notes: str | None = None


@router.post("/corrections", status_code=201)
async def request_correction(payload: CorrectionIn, request: Request, user: dict = Depends(require_permission(P_ATTENDANCE_CORRECTION_REQUEST))):
    if payload.subject_kind not in {"student", "staff"}:
        raise HTTPException(status_code=400, detail="subject_kind must be student|staff")
    if payload.new_status not in ATTENDANCE_STATUS:
        raise HTTPException(status_code=400, detail=f"Allowed status: {ATTENDANCE_STATUS}")
    db = get_db()
    tid = user["tenant_id"]
    coll = db.student_attendance if payload.subject_kind == "student" else db.staff_attendance
    key = "student_id" if payload.subject_kind == "student" else "employee_id"
    att = await coll.find_one({"tenant_id": tid, key: payload.subject_id, "date": payload.date})
    if not att:
        raise HTTPException(status_code=404, detail="Attendance record not found for the given date/subject")
    doc = AttendanceCorrection(
        tenant_id=tid, subject_kind=payload.subject_kind, subject_id=payload.subject_id,
        attendance_id=str(att["_id"]), date=payload.date,
        old_status=att.get("status"), new_status=payload.new_status,
        old_notes=att.get("notes") or att.get("override_notes"),
        new_notes=payload.new_notes, reason=payload.reason,
        requested_by_user_id=user["id"],
    ).to_mongo()
    res = await db.attendance_corrections.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="attendance.correction.request", resource="attendance_correction",
                    resource_id=str(res.inserted_id), tenant_id=tid, actor=user, request=request,
                    metadata={"subject_kind": payload.subject_kind, "subject_id": payload.subject_id})
    return _out(doc)


@router.get("/corrections")
async def list_corrections(status: str | None = None, user: dict = Depends(require_permission(P_ATTENDANCE_VIEW))):
    q: dict = {"tenant_id": user["tenant_id"]}
    if status: q["status"] = status
    docs = await get_db().attendance_corrections.find(q).sort("created_at", -1).to_list(500)
    return [_out(d) for d in docs]


@router.post("/corrections/{cid}/approve")
async def approve_correction(cid: str, payload: DecisionIn, request: Request, user: dict = Depends(require_permission(P_ATTENDANCE_CORRECTION_APPROVE))):
    db = get_db()
    tid = user["tenant_id"]
    old = await db.attendance_corrections.find_one({"_id": _oid(cid), "tenant_id": tid})
    if not old: raise HTTPException(status_code=404, detail="Correction not found")
    if old["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot approve — current status {old['status']}")
    coll = db.student_attendance if old["subject_kind"] == "student" else db.staff_attendance
    att = await coll.find_one({"_id": _oid(old["attendance_id"]), "tenant_id": tid})
    if not att:
        raise HTTPException(status_code=404, detail="Target attendance record missing")
    # Apply — preserve old value on the correction, never silently overwrite history on the day doc.
    await coll.update_one({"_id": att["_id"]}, {"$set": {
        "status": old["new_status"], "notes": old.get("new_notes"),
        "overridden_by_user_id": user["id"], "overridden_at": _now(),
        "override_notes": f"Correction {cid}: {old.get('reason')}",
        "updated_at": _now(),
    }})
    await db.attendance_corrections.update_one({"_id": old["_id"]}, {"$set": {
        "status": "approved", "approver_user_id": user["id"],
        "decision_at": _now(), "decision_reason": payload.reason,
        "applied_at": _now(), "updated_at": _now(),
    }})
    await log_event(action="attendance.correction.approve", resource="attendance_correction",
                    resource_id=cid, tenant_id=tid, actor=user, request=request,
                    old_value={"status": old.get("old_status")},
                    new_value={"status": old["new_status"]},
                    metadata={"attendance_id": old["attendance_id"], "reason": payload.reason})
    return _out(await db.attendance_corrections.find_one({"_id": old["_id"]}))


@router.post("/corrections/{cid}/reject")
async def reject_correction(cid: str, payload: DecisionIn, request: Request, user: dict = Depends(require_permission(P_ATTENDANCE_CORRECTION_APPROVE))):
    db = get_db()
    old = await db.attendance_corrections.find_one({"_id": _oid(cid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Correction not found")
    if old["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot reject — current status {old['status']}")
    await db.attendance_corrections.update_one({"_id": old["_id"]}, {"$set": {
        "status": "rejected", "approver_user_id": user["id"],
        "decision_at": _now(), "decision_reason": payload.reason, "updated_at": _now(),
    }})
    await log_event(action="attendance.correction.reject", resource="attendance_correction",
                    resource_id=cid, tenant_id=user["tenant_id"], actor=user, request=request,
                    metadata={"reason": payload.reason})
    return _out(await db.attendance_corrections.find_one({"_id": old["_id"]}))


@router.post("/corrections/{cid}/cancel")
async def cancel_correction(cid: str, request: Request, user: dict = Depends(require_permission(P_ATTENDANCE_CORRECTION_REQUEST))):
    db = get_db()
    old = await db.attendance_corrections.find_one({"_id": _oid(cid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Correction not found")
    if old["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot cancel — current status {old['status']}")
    await db.attendance_corrections.update_one({"_id": old["_id"]}, {"$set": {
        "status": "cancelled", "decision_at": _now(), "updated_at": _now(),
    }})
    return _out(await db.attendance_corrections.find_one({"_id": old["_id"]}))


# ============================================================
# Overview — dashboard rollup
# ============================================================
@router.get("/overview")
async def overview(user: dict = Depends(require_permission(P_ATTENDANCE_VIEW))):
    db = get_db()
    tid = user["tenant_id"]
    today = _today_iso()
    base_s = {"tenant_id": tid, "date": today}
    staff_present = await db.staff_attendance.count_documents({**base_s, "status": {"$in": ["present", "late", "half_day"]}})
    staff_absent = await db.staff_attendance.count_documents({**base_s, "status": "absent"})
    student_present = await db.student_attendance.count_documents({**base_s, "status": {"$in": ["present", "late"]}})
    student_absent = await db.student_attendance.count_documents({**base_s, "status": "absent"})
    pending_corr = await db.attendance_corrections.count_documents({"tenant_id": tid, "status": "pending"})
    pending_off = await db.off_campus_exceptions.count_documents({"tenant_id": tid, "status": "pending"})
    active_tokens = await db.student_qr_tokens.count_documents({"tenant_id": tid, "status": "active"})
    return {
        "date": today,
        "staff": {"present": staff_present, "absent": staff_absent},
        "student": {"present": student_present, "absent": student_absent},
        "pending_corrections": pending_corr,
        "pending_off_campus": pending_off,
        "active_qr_tokens": active_tokens,
    }
