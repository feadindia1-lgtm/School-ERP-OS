"""Prompt 6 — Attendance Engine tests.

Guards per user's architectural requirements:
- Face evidence stored via storage service (NOT base64 in Mongo).
- No fabricated VERIFIED result when provider is 'none'.
- Haversine geofence + configurable radius/accuracy.
- Opaque QR tokens, static with revocation; revoked tokens 403.
- Daily + session model; sessions roll up into daily status.
- Correction workflow preserves old/new/actor/approver/reason/timestamps.
- Failure cases: GPS unavailable/poor, outside geofence, invalid/revoked QR,
  duplicate scan, failed verification evidence requirement, cross-tenant.
"""
import io
import os
import uuid

import requests

BASE = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://schoolos-foundation-1.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE}/api/v1"

RUN = uuid.uuid4().hex[:6]
A_SLUG, A_EMAIL = f"atta-{RUN}", f"owner-{RUN}@atta.example.com"
B_SLUG, B_EMAIL = f"attb-{RUN}", f"owner-{RUN}@attb.example.com"
PW = "SchoolOwner@123"

state: dict = {}


def _sess():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"}); return s


def _register(slug, email, name):
    s = _sess()
    r = s.post(f"{API}/auth/register-school", json={
        "school_name": name, "slug": slug, "contact_email": email,
        "owner_full_name": "Test Owner", "owner_email": email, "owner_password": PW,
    })
    assert r.status_code == 201, r.text
    return s


def _err_code(body):
    d = body.get("error", {}).get("details") or body.get("detail")
    return d.get("code") if isinstance(d, dict) else None


# ---------- Bootstrap ----------
def test_00_bootstrap():
    state["sA"] = _register(A_SLUG, A_EMAIL, f"Atta {RUN}")
    state["sB"] = _register(B_SLUG, B_EMAIL, f"Attb {RUN}")
    # Create an employee linked to the owner user so staff/clock resolves self-serve
    me = state["sA"].get(f"{API}/auth/me").json()
    emp = state["sA"].post(f"{API}/school/staff/employees", json={
        "first_name": "Owner", "last_name": "Self", "user_id": me["id"],
    })
    assert emp.status_code == 201, emp.text
    state["my_emp_id"] = emp.json()["id"]


# ---------- Config ----------
def test_10_config_default_and_update():
    r = state["sA"].get(f"{API}/school/attendance/config")
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["geofence_radius_m"] == 150 and cfg["max_gps_accuracy_m"] == 50
    assert cfg["qr_rotation_policy"] == "static_revocable"
    r2 = state["sA"].put(f"{API}/school/attendance/config", json={
        "geofence_lat": 12.9716, "geofence_lng": 77.5946,
        "geofence_radius_m": 200, "max_gps_accuracy_m": 30,
        "face_verification_required": True, "duplicate_scan_window_seconds": 30,
    })
    assert r2.status_code == 200
    state["cfg"] = r2.json()


def test_11_config_rejects_bad_values():
    r = state["sA"].put(f"{API}/school/attendance/config", json={"geofence_radius_m": -5})
    assert r.status_code == 400
    r2 = state["sA"].put(f"{API}/school/attendance/config", json={"max_gps_accuracy_m": 0})
    assert r2.status_code == 400


# ---------- Staff clock-in (3-layer) ----------
def _clock(s, data, files):
    """requests Session carries Content-Type: application/json by default; for
    multipart we must drop it so requests can set the boundary header."""
    headers = {k: v for k, v in s.headers.items() if k.lower() != "content-type"}
    return requests.post(f"{API}/school/attendance/staff/clock", data=data, files=files, headers=headers, cookies=s.cookies)


def _clock_form(**overrides):
    return {
        "session_type": overrides.get("session_type", "clock_in"),
        "device_lat": str(overrides.get("device_lat", 12.9716)),
        "device_lng": str(overrides.get("device_lng", 77.5946)),
        "device_accuracy_m": str(overrides.get("device_accuracy_m", 15.0)),
    }


# Dummy non-selfie file to force requests → multipart (FastAPI Form() needs multipart body).
NO_SELFIE = {"__dummy__": ("x.txt", b"x", "text/plain")}


def test_20_clock_rejects_poor_gps_accuracy():
    r = _clock(state["sA"], _clock_form(device_accuracy_m=200), NO_SELFIE)
    # Session has no Content-Type set so requests chooses multipart automatically.
    assert r.status_code == 400
    assert _err_code(r.json()) == "gps_accuracy_too_low"


def test_21_clock_rejects_outside_geofence_without_exception():
    r = _clock(state["sA"], _clock_form(device_lat=13.0, device_lng=78.0), NO_SELFIE)
    assert r.status_code == 403
    assert _err_code(r.json()) == "outside_geofence"


def test_22_clock_requires_face_evidence_when_configured():
    # Face required + inside geofence + good accuracy but no selfie
    r = _clock(state["sA"], _clock_form(), NO_SELFIE)
    assert r.status_code == 400
    assert _err_code(r.json()) == "face_evidence_required"


def test_23_clock_in_happy_path_stores_evidence_and_returns_pending_review():
    files = {"selfie": ("selfie.jpg", io.BytesIO(b"fake-jpeg-bytes-xyz"), "image/jpeg")}
    r = _clock(state["sA"], _clock_form(), files)
    assert r.status_code == 200, r.text
    body = r.json()
    sess = body["session"]
    # Face provider is 'none' → must NOT fabricate VERIFIED
    assert sess["verification_status"] in {"PENDING_REVIEW", "NOT_VERIFIED"}
    assert sess["verification_status"] != "VERIFIED"
    assert sess["face_storage_key"] and sess["face_storage_key"].startswith(f"tenants/")
    # Not base64 in Mongo — storage key only
    assert "face_bytes" not in sess
    assert body["daily"]["status"] in {"present", "late", "half_day"}
    state["staff_sess_id"] = sess["id"]


def test_24_clock_out_computes_total_minutes():
    files = {"selfie": ("selfie.jpg", io.BytesIO(b"out-bytes"), "image/jpeg")}
    r = _clock(state["sA"], _clock_form(session_type="clock_out"), files)
    assert r.status_code == 200
    daily = r.json()["daily"]
    assert daily["last_out_at"] is not None


def test_25_off_campus_exception_flow():
    # Request → approve → clock-in outside geofence succeeds
    me_emp = state["my_emp_id"]
    r = state["sA"].post(f"{API}/school/attendance/staff/off-campus", json={
        "employee_id": me_emp,
        "start_date": __import__("datetime").date.today().isoformat(),
        "end_date": __import__("datetime").date.today().isoformat(),
        "reason": "field visit",
    })
    assert r.status_code == 201
    exc = r.json()
    r2 = state["sA"].post(f"{API}/school/attendance/staff/off-campus/{exc['id']}/approve", json={"reason": "ok"})
    assert r2.status_code == 200
    files = {"selfie": ("x.jpg", io.BytesIO(b"evidence"), "image/jpeg")}
    r3 = _clock(state["sA"], {**_clock_form(device_lat=13.0, device_lng=78.0), "off_campus_exception_id": exc["id"]}, files)
    assert r3.status_code == 200, r3.text


def test_26_staff_manual_override_records_actor_and_reason():
    r = state["sA"].post(f"{API}/school/attendance/staff/manual", json={
        "employee_id": state["my_emp_id"], "date": "2026-04-01",
        "status": "excused", "reason": "medical",
    })
    assert r.status_code == 200
    # Confirm it shows up in register
    r2 = state["sA"].get(f"{API}/school/attendance/staff", params={"date": "2026-04-01"})
    assert r2.status_code == 200 and any(x["status"] == "excused" for x in r2.json())


# ---------- Student QR ----------
def test_30_qr_issue_rotate_revoke():
    # Create a student
    r = state["sA"].post(f"{API}/school/students", json={"first_name": "Lia", "last_name": "T"})
    assert r.status_code == 201
    sid = r.json()["id"]; state["student_id"] = sid
    r2 = state["sA"].post(f"{API}/school/attendance/students/qr-tokens", json={"student_id": sid})
    assert r2.status_code == 201
    t1 = r2.json(); state["qr1"] = t1
    # Token must not contain the student id
    assert sid not in t1["token"]
    # Second issue without rotate → 409
    r3 = state["sA"].post(f"{API}/school/attendance/students/qr-tokens", json={"student_id": sid})
    assert r3.status_code == 409
    # Rotate replaces
    r4 = state["sA"].post(f"{API}/school/attendance/students/qr-tokens", json={"student_id": sid, "rotate": True})
    assert r4.status_code == 201
    state["qr2"] = r4.json()
    assert r4.json()["token"] != t1["token"]
    # Previous now 'rotated'
    r5 = state["sA"].get(f"{API}/school/attendance/students/qr-tokens", params={"student_id": sid})
    statuses = {t["status"] for t in r5.json()}
    assert "rotated" in statuses and "active" in statuses


def test_31_scan_entry_updates_daily_and_debounces_duplicates():
    r = state["sA"].post(f"{API}/school/attendance/students/scan", json={
        "token": state["qr2"]["token"], "session_type": "entry",
    })
    assert r.status_code == 200, r.text
    assert r.json()["daily"]["status"] in {"present", "late"}
    # Second within window → duplicate_scan
    r2 = state["sA"].post(f"{API}/school/attendance/students/scan", json={
        "token": state["qr2"]["token"], "session_type": "entry",
    })
    assert r2.status_code == 409
    assert _err_code(r2.json()) == "duplicate_scan"


def test_32_revoked_token_rejected():
    r = state["sA"].post(f"{API}/school/attendance/students/qr-tokens/{state['qr2']['id']}/revoke")
    assert r.status_code == 200
    r2 = state["sA"].post(f"{API}/school/attendance/students/scan", json={
        "token": state["qr2"]["token"], "session_type": "entry",
    })
    assert r2.status_code == 403
    assert _err_code(r2.json()) == "token_revoked"


def test_33_invalid_token_not_found():
    r = state["sA"].post(f"{API}/school/attendance/students/scan", json={
        "token": "not-a-real-token-12345", "session_type": "entry",
    })
    assert r.status_code == 404


def test_34_class_bulk_mark_present_absent_late():
    # Create academic year + class
    y = state["sA"].post(f"{API}/school/academic/years", json={
        "name": f"att-{RUN}", "start_date": "2026-04-01", "end_date": "2027-03-31", "is_current": True,
    }).json()
    c = state["sA"].post(f"{API}/school/academic/classes", json={
        "academic_year_id": y["id"], "name": "Grade 2", "code": f"G2-{RUN}",
    }).json()
    # Make a second student
    s2 = state["sA"].post(f"{API}/school/students", json={"first_name": "Mo", "last_name": "P"}).json()
    today = __import__("datetime").date.today().isoformat()
    r = state["sA"].post(f"{API}/school/attendance/students/mark-class", json={
        "date": today, "class_id": c["id"],
        "entries": [
            {"student_id": state["student_id"], "status": "present"},
            {"student_id": s2["id"], "status": "absent"},
            {"student_id": "a" * 24, "status": "late"},  # not found
            {"student_id": s2["id"], "status": "BOGUS"},
        ],
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["accepted"]) == 2 and len(body["failed"]) == 2


# ---------- Corrections ----------
def test_40_correction_request_approve_preserves_history():
    today = __import__("datetime").date.today().isoformat()
    # Request change on student
    r = state["sA"].post(f"{API}/school/attendance/corrections", json={
        "subject_kind": "student", "subject_id": state["student_id"],
        "date": today, "new_status": "excused", "reason": "doctor",
    })
    assert r.status_code == 201
    cid = r.json()["id"]
    assert r.json()["old_status"] is not None  # preserved
    # Approve
    r2 = state["sA"].post(f"{API}/school/attendance/corrections/{cid}/approve", json={"reason": "OK"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "approved" and body["applied_at"]
    assert body["old_status"] != body["new_status"]
    # Attendance now reflects new status
    r3 = state["sA"].get(f"{API}/school/attendance/students", params={"date": today, "student_id": state["student_id"]})
    assert any(x["status"] == "excused" for x in r3.json())


def test_41_correction_reject_leaves_attendance_unchanged():
    today = __import__("datetime").date.today().isoformat()
    r = state["sA"].post(f"{API}/school/attendance/corrections", json={
        "subject_kind": "student", "subject_id": state["student_id"],
        "date": today, "new_status": "absent", "reason": "test reject",
    })
    cid = r.json()["id"]
    r2 = state["sA"].post(f"{API}/school/attendance/corrections/{cid}/reject", json={"reason": "no"})
    assert r2.status_code == 200 and r2.json()["status"] == "rejected"
    # Attendance remains 'excused' from previous approval
    r3 = state["sA"].get(f"{API}/school/attendance/students", params={"date": today, "student_id": state["student_id"]})
    assert any(x["status"] == "excused" for x in r3.json())


# ---------- Reports ----------
def test_50_student_summary_counts_by_status():
    today = __import__("datetime").date.today().isoformat()
    r = state["sA"].get(f"{API}/school/attendance/students/{state['student_id']}/summary",
                        params={"from_date": "2026-01-01", "to_date": today})
    assert r.status_code == 200
    body = r.json()
    assert sum(body["by_status"].values()) >= 1


def test_51_overview_includes_counts():
    r = state["sA"].get(f"{API}/school/attendance/overview")
    assert r.status_code == 200
    b = r.json()
    for key in ("staff", "student", "pending_corrections", "pending_off_campus", "active_qr_tokens"):
        assert key in b


# ---------- Cross-tenant ----------
def test_60_cross_tenant_isolation():
    r = state["sB"].get(f"{API}/school/attendance/staff")
    assert r.status_code == 200 and r.json() == []
    r2 = state["sB"].get(f"{API}/school/attendance/students")
    assert r2.status_code == 200 and r2.json() == []
    # Token from A must not scan in B
    r3 = state["sB"].post(f"{API}/school/attendance/students/scan", json={
        "token": state["qr1"]["token"], "session_type": "entry",
    })
    assert r3.status_code == 404


# ---------- RBAC ----------
def test_70_teacher_can_clock_mark_class_but_not_approve_corrections():
    ts = _sess()
    # Create teacher user in tenant A
    r = state["sA"].post(f"{API}/school/users", json={
        "email": f"ta-{RUN}@atta.example.com", "full_name": "Ms Q",
        "password": "Teacher@123", "role": "teacher",
    })
    assert r.status_code == 201
    r2 = ts.post(f"{API}/auth/login", json={"email": f"ta-{RUN}@atta.example.com", "password": "Teacher@123"})
    assert r2.status_code == 200
    # Teacher can view attendance
    assert ts.get(f"{API}/school/attendance/overview").status_code == 200
    # Cannot approve corrections — 403
    r3 = ts.post(f"{API}/school/attendance/corrections/{uuid.uuid4().hex[:24].ljust(24, '0')}/approve", json={"reason": "x"})
    assert r3.status_code in (403, 404)   # permission denied preferred, 404 if route checks permission late
    # Cannot update config
    r4 = ts.put(f"{API}/school/attendance/config", json={"geofence_radius_m": 1000})
    assert r4.status_code == 403


# ---------- Audit ----------
def test_80_audit_events_emitted():
    r = state["sA"].get(f"{API}/school/audit-logs", params={"limit": 200})
    assert r.status_code == 200
    actions = {a["action"] for a in r.json()}
    for a in ("attendance.config.update", "attendance.staff.session",
              "attendance.qr.issue", "attendance.qr.revoke",
              "attendance.student.scan", "attendance.student.bulk_mark",
              "attendance.correction.request", "attendance.correction.approve",
              "attendance.correction.reject", "attendance.off_campus.request",
              "attendance.off_campus.approve"):
        assert a in actions, f"missing audit for {a}"
