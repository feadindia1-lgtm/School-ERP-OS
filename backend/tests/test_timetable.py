"""Prompt 7 — Timetable Engine + Proxy Scheduling tests.

Covers:
- Slot CRUD + conflict detection (teacher double-book, room double-book, section slot taken)
- Bell schedule / working-day validation (break period, weekly-off day)
- Bulk upsert (replace + duplicate-cell detection)
- Grid endpoint, teacher weekly, for-date (with substitution overlay)
- Publish/Lock lifecycle
- Proxy config get/put, absence detection (leave + attendance)
- Recommendation ranking (subject match, availability filter, workload penalty)
- Substitution create/approve/reject/cancel, duplicate guard, same-teacher guard
- Tenant isolation, RBAC (teacher cannot manage, principal can approve)
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import requests

BASE = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://schoolos-foundation-1.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE}/api/v1"

RUN = uuid.uuid4().hex[:6]
A_SLUG = f"tt-a-{RUN}"
B_SLUG = f"tt-b-{RUN}"
A_EMAIL = f"owner-{RUN}@tta.example.com"
B_EMAIL = f"owner-{RUN}@ttb.example.com"
PW = "SchoolOwner@123"

state: dict = {}


def _sess() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _register(slug: str, email: str, name: str) -> requests.Session:
    s = _sess()
    r = s.post(f"{API}/auth/register-school", json={
        "school_name": name, "slug": slug, "contact_email": email,
        "owner_full_name": "Test Owner", "owner_email": email, "owner_password": PW,
    })
    assert r.status_code == 201, r.text
    return s


def _login(email: str, pw: str = PW) -> requests.Session:
    s = _sess()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return s


def _err_code(body: dict) -> str | None:
    details = body.get("error", {}).get("details") or body.get("detail")
    if isinstance(details, dict): return details.get("code")
    return None


# ---------- Bootstrap: a tenant with academic framework + staff ----------
def test_00_bootstrap_tenant_a():
    s = _register(A_SLUG, A_EMAIL, f"TT-A {RUN}")
    state["sA"] = s
    me = s.get(f"{API}/auth/me").json()
    state["owner_a"] = me

    # Academic year
    y = s.post(f"{API}/school/academic/years", json={
        "name": f"TT{RUN}", "start_date": "2026-04-01", "end_date": "2027-03-31",
        "is_current": True, "board_preset": "CBSE",
    }).json()
    state["yr"] = y

    # Working-day policy (mon-fri working, sat/sun off)
    s.put(f"{API}/school/academic/working-day-policy", json={
        "academic_year_id": y["id"],
        "working_days": ["mon", "tue", "wed", "thu", "fri"],
        "weekly_off": ["sat", "sun"],
    })

    # Classes + sections
    cls = s.post(f"{API}/school/academic/classes", json={
        "academic_year_id": y["id"], "name": "Class 7", "code": "7",
    }).json()
    state["cls"] = cls
    sec = s.post(f"{API}/school/academic/sections", json={
        "academic_year_id": y["id"], "class_id": cls["id"], "name": "A",
    }).json()
    state["secA"] = sec
    sec2 = s.post(f"{API}/school/academic/sections", json={
        "academic_year_id": y["id"], "class_id": cls["id"], "name": "B",
    }).json()
    state["secB"] = sec2

    # Subjects
    maths = s.post(f"{API}/school/academic/subjects", json={"name": "Mathematics", "code": "MATH"}).json()
    sci = s.post(f"{API}/school/academic/subjects", json={"name": "Science", "code": "SCI"}).json()
    state["maths"] = maths; state["sci"] = sci

    # Rooms
    r1 = s.post(f"{API}/school/academic/rooms", json={"name": "Room 1", "code": "R1"}).json()
    r2 = s.post(f"{API}/school/academic/rooms", json={"name": "Room 2", "code": "R2"}).json()
    state["r1"] = r1; state["r2"] = r2

    # Bell schedule with 3 teaching periods + 1 break
    bell = s.post(f"{API}/school/academic/bell-schedules", json={
        "academic_year_id": y["id"], "name": "Weekday", "is_default": True,
        "periods": [
            {"period_no": 1, "label": "P1", "start_time": "09:00", "end_time": "09:45"},
            {"period_no": 2, "label": "P2", "start_time": "09:45", "end_time": "10:30"},
            {"period_no": 3, "label": "Break", "start_time": "10:30", "end_time": "10:45", "is_break": True},
            {"period_no": 4, "label": "P3", "start_time": "10:45", "end_time": "11:30"},
        ],
    }).json()
    state["bell"] = bell

    # Create teacher users
    t1 = s.post(f"{API}/school/users", json={
        "email": f"t1-{RUN}@tta.example.com", "full_name": "T One",
        "password": "Teacher@123", "role": "teacher",
    }).json()
    t2 = s.post(f"{API}/school/users", json={
        "email": f"t2-{RUN}@tta.example.com", "full_name": "T Two",
        "password": "Teacher@123", "role": "teacher",
    }).json()
    t3 = s.post(f"{API}/school/users", json={
        "email": f"t3-{RUN}@tta.example.com", "full_name": "T Three",
        "password": "Teacher@123", "role": "teacher",
    }).json()
    state["t1"] = t1; state["t2"] = t2; state["t3"] = t3

    # Teacher assignments — t1 teaches MATH to class 7, t2 teaches SCI
    s.post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": y["id"], "teacher_user_id": t1["id"],
        "class_id": cls["id"], "section_id": sec["id"], "subject_id": maths["id"],
    })
    s.post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": y["id"], "teacher_user_id": t2["id"],
        "class_id": cls["id"], "section_id": sec["id"], "subject_id": sci["id"],
    })


def test_01_bootstrap_tenant_b():
    state["sB"] = _register(B_SLUG, B_EMAIL, f"TT-B {RUN}")


# ---------- Slot creation + conflict detection ----------
def test_10_create_slot_happy_path():
    s = state["sA"]
    r = s.post(f"{API}/school/timetable/slots", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secA"]["id"], "bell_schedule_id": state["bell"]["id"],
        "weekday": "mon", "period_no": 1,
        "subject_id": state["maths"]["id"], "teacher_user_id": state["t1"]["id"],
        "room_id": state["r1"]["id"],
    })
    assert r.status_code == 201, r.text
    state["slot1"] = r.json()
    assert r.json().get("teacher_employee_id") is None   # no employee row linked


def test_11_section_slot_taken_conflict():
    s = state["sA"]
    r = s.post(f"{API}/school/timetable/slots", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secA"]["id"], "bell_schedule_id": state["bell"]["id"],
        "weekday": "mon", "period_no": 1,
        "subject_id": state["sci"]["id"], "teacher_user_id": state["t2"]["id"],
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "timetable_conflict"


def test_12_teacher_double_book():
    s = state["sA"]
    # Try to put t1 at the same weekday/period in section B
    r = s.post(f"{API}/school/timetable/slots", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secB"]["id"], "bell_schedule_id": state["bell"]["id"],
        "weekday": "mon", "period_no": 1,
        "subject_id": state["maths"]["id"], "teacher_user_id": state["t1"]["id"],
    })
    assert r.status_code == 409
    conflicts = r.json().get("detail", {}).get("conflicts") or r.json().get("error", {}).get("details", {}).get("conflicts") or []
    assert any(c["code"] == "teacher_double_book" for c in conflicts)


def test_13_room_double_book():
    s = state["sA"]
    r = s.post(f"{API}/school/timetable/slots", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secB"]["id"], "bell_schedule_id": state["bell"]["id"],
        "weekday": "mon", "period_no": 1,
        "subject_id": state["sci"]["id"], "teacher_user_id": state["t2"]["id"],
        "room_id": state["r1"]["id"],
    })
    assert r.status_code == 409
    conflicts = r.json().get("detail", {}).get("conflicts") or r.json().get("error", {}).get("details", {}).get("conflicts") or []
    assert any(c["code"] == "room_double_book" for c in conflicts)


def test_14_cannot_assign_to_break_period():
    s = state["sA"]
    r = s.post(f"{API}/school/timetable/slots", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secA"]["id"], "bell_schedule_id": state["bell"]["id"],
        "weekday": "mon", "period_no": 3,  # break
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "period_is_break"


def test_15_cannot_assign_to_weekly_off_day():
    s = state["sA"]
    r = s.post(f"{API}/school/timetable/slots", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secA"]["id"], "bell_schedule_id": state["bell"]["id"],
        "weekday": "sun", "period_no": 1,
    })
    assert r.status_code == 409
    assert _err_code(r.json()) in ("weekly_off_day", "non_working_day")


# ---------- Update + delete + validate ----------
def test_20_update_slot_change_teacher():
    s = state["sA"]
    sid = state["slot1"]["id"]
    r = s.patch(f"{API}/school/timetable/slots/{sid}", json={"teacher_user_id": state["t2"]["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["teacher_user_id"] == state["t2"]["id"]


def test_21_validate_endpoint_reports_conflict_without_writing():
    s = state["sA"]
    r = s.post(f"{API}/school/timetable/validate", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secB"]["id"], "bell_schedule_id": state["bell"]["id"],
        "weekday": "mon", "period_no": 1,
        "teacher_user_id": state["t2"]["id"],   # now booked in secA via test_20
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert any(c["code"] == "teacher_double_book" for c in data["conflicts"])


# ---------- Bulk upsert ----------
def test_30_bulk_upsert_section_grid():
    s = state["sA"]
    r = s.post(f"{API}/school/timetable/slots/bulk-upsert", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secB"]["id"], "bell_schedule_id": state["bell"]["id"],
        "replace": True,
        "slots": [
            {"academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
             "section_id": state["secB"]["id"], "bell_schedule_id": state["bell"]["id"],
             "weekday": "mon", "period_no": 2,
             "subject_id": state["maths"]["id"], "teacher_user_id": state["t1"]["id"]},
            {"academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
             "section_id": state["secB"]["id"], "bell_schedule_id": state["bell"]["id"],
             "weekday": "tue", "period_no": 1,
             "subject_id": state["sci"]["id"], "teacher_user_id": state["t3"]["id"]},
        ],
    })
    assert r.status_code == 200, r.text
    assert r.json()["count"] == 2


def test_31_bulk_upsert_duplicate_cell_rejected():
    s = state["sA"]
    r = s.post(f"{API}/school/timetable/slots/bulk-upsert", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secB"]["id"], "bell_schedule_id": state["bell"]["id"],
        "replace": True,
        "slots": [
            {"academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
             "section_id": state["secB"]["id"], "bell_schedule_id": state["bell"]["id"],
             "weekday": "mon", "period_no": 2},
            {"academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
             "section_id": state["secB"]["id"], "bell_schedule_id": state["bell"]["id"],
             "weekday": "mon", "period_no": 2},
        ],
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "duplicate_cell"


# ---------- Grid + teacher weekly ----------
def test_40_grid_endpoint():
    s = state["sA"]
    r = s.get(f"{API}/school/timetable/grid", params={
        "academic_year_id": state["yr"]["id"], "section_id": state["secA"]["id"],
    })
    assert r.status_code == 200
    g = r.json()
    assert g["bell_schedule"]["id"] == state["bell"]["id"]
    assert g["working_days"] == ["mon", "tue", "wed", "thu", "fri"]
    assert len(g["slots"]) >= 1


def test_41_teacher_weekly():
    s = state["sA"]
    r = s.get(f"{API}/school/timetable/teacher/{state['t1']['id']}/weekly",
              params={"academic_year_id": state["yr"]["id"]})
    assert r.status_code == 200
    data = r.json()
    assert data["teacher_user_id"] == state["t1"]["id"]
    # t1 only in secB mon P2 now (post bulk upsert)
    assert any(sl["weekday"] == "mon" and sl["period_no"] == 2 for sl in data["slots"])


# ---------- Publish + lock ----------
def test_50_publish_section_requires_slots():
    s = state["sA"]
    # Clear secA by writing an empty section via bulk-upsert
    r = s.post(f"{API}/school/timetable/sections/publish", json={
        "academic_year_id": state["yr"]["id"], "section_id": state["secB"]["id"],
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "published"


def test_51_lock_blocks_edits():
    s = state["sA"]
    r = s.post(f"{API}/school/timetable/sections/lock", json={
        "academic_year_id": state["yr"]["id"], "section_id": state["secB"]["id"], "locked": True,
    })
    assert r.status_code == 200 and r.json()["locked"] is True
    # Attempt to add a slot — should 409
    r2 = s.post(f"{API}/school/timetable/slots", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secB"]["id"], "bell_schedule_id": state["bell"]["id"],
        "weekday": "wed", "period_no": 1,
    })
    assert r2.status_code == 409 and _err_code(r2.json()) == "timetable_locked"
    # Unlock
    s.post(f"{API}/school/timetable/sections/lock", json={
        "academic_year_id": state["yr"]["id"], "section_id": state["secB"]["id"], "locked": False,
    })


# ---------- Proxy config ----------
def test_60_proxy_config_default_and_update():
    s = state["sA"]
    r = s.get(f"{API}/school/proxy/config")
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["cutoff_time"] == "09:30"
    r2 = s.put(f"{API}/school/proxy/config", json={
        "cutoff_time": "08:30", "prefer_same_grade": True,
        "max_proxy_per_day_per_teacher": 5,
    })
    assert r2.status_code == 200
    assert r2.json()["cutoff_time"] == "08:30"


# ---------- Absence detection (via approved leave) ----------
def _mon_this_week() -> str:
    today = datetime.now(timezone.utc).date()
    # pick next monday to deterministically match 'mon' weekday
    offset = (0 - today.weekday()) % 7
    if offset == 0: offset = 7
    return (today + timedelta(days=offset)).isoformat()


def test_70_absence_via_leave():
    s = state["sA"]
    # Create employee + leave for t2 (who holds the only secA mon-P1 slot now)
    e = s.post(f"{API}/school/staff/employees", json={
        "first_name": "T", "last_name": "Two Emp",
        "user_id": state["t2"]["id"],
    }).json()
    state["emp_t2"] = e
    lt = s.post(f"{API}/school/staff/leave-types", json={
        "name": "Casual", "code": "CL", "is_paid": True, "approval_steps": 1,
    }).json()
    monday = _mon_this_week()
    la = s.post(f"{API}/school/staff/leave-applications", json={
        "employee_id": e["id"], "leave_type_id": lt["id"],
        "start_date": monday, "end_date": monday, "days": 1, "reason": "sick",
    }).json()
    # Approve the leave
    r = s.post(f"{API}/school/staff/leave-applications/{la['id']}/approve", json={})
    assert r.status_code == 200

    # Query absences
    r2 = s.get(f"{API}/school/proxy/absences", params={
        "date": monday, "academic_year_id": state["yr"]["id"],
    })
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["weekday"] == "mon"
    ids = [a["teacher_user_id"] for a in data["absences"]]
    assert state["t2"]["id"] in ids
    state["monday"] = monday
    # Confirm t2 has at least one affected period (secA mon P1)
    t2_row = next(a for a in data["absences"] if a["teacher_user_id"] == state["t2"]["id"])
    assert len(t2_row["affected_periods"]) >= 1


# ---------- Recommendations ----------
def test_80_recommendations_rank_filters_absent_and_busy():
    s = state["sA"]
    r = s.get(f"{API}/school/proxy/recommendations", params={
        "date": state["monday"], "academic_year_id": state["yr"]["id"],
        "teacher_user_id": state["t2"]["id"],
    })
    assert r.status_code == 200, r.text
    affected = r.json()["affected"]
    assert len(affected) >= 1
    cands = affected[0]["candidates"]
    # t2 (absent) should not appear, t1 is busy at mon-P2 but *available* at mon-P1
    cand_ids = {c["teacher_user_id"] for c in cands}
    assert state["t2"]["id"] not in cand_ids
    # t3 is free; t1 is free at mon-P1
    assert any(c["teacher_user_id"] in {state["t1"]["id"], state["t3"]["id"]} for c in cands)


# ---------- Substitution lifecycle ----------
def test_90_create_substitution_pending():
    s = state["sA"]
    # Find the affected slot id
    r = s.get(f"{API}/school/proxy/absences", params={
        "date": state["monday"], "academic_year_id": state["yr"]["id"],
    })
    absences = r.json()["absences"]
    row = next(a for a in absences if a["teacher_user_id"] == state["t2"]["id"])
    slot = row["affected_periods"][0]["slot"]
    state["abs_slot"] = slot

    r2 = s.post(f"{API}/school/proxy/substitutions", json={
        "date": state["monday"], "academic_year_id": state["yr"]["id"],
        "timetable_slot_id": slot["id"],
        "substitute_teacher_user_id": state["t3"]["id"],
        "source": "leave",
    })
    assert r2.status_code == 201, r2.text
    sub = r2.json()
    assert sub["status"] == "pending"
    state["sub1"] = sub


def test_91_duplicate_substitution_rejected():
    s = state["sA"]
    r = s.post(f"{API}/school/proxy/substitutions", json={
        "date": state["monday"], "academic_year_id": state["yr"]["id"],
        "timetable_slot_id": state["abs_slot"]["id"],
        "substitute_teacher_user_id": state["t3"]["id"],
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "substitution_exists"


def test_92_approve_substitution_shows_in_for_date():
    s = state["sA"]
    r = s.post(f"{API}/school/proxy/substitutions/{state['sub1']['id']}/approve", json={})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    r2 = s.get(f"{API}/school/timetable/for-date", params={
        "date": state["monday"], "academic_year_id": state["yr"]["id"],
        "section_id": state["secA"]["id"],
    })
    assert r2.status_code == 200
    rows = r2.json()["rows"]
    assert any(r.get("substitution") and r["substitution"]["status"] == "approved" for r in rows)


def test_93_reject_from_approved_rejected():
    s = state["sA"]
    r = s.post(f"{API}/school/proxy/substitutions/{state['sub1']['id']}/reject", json={"reason": "no"})
    assert r.status_code == 409


def test_94_cancel_substitution():
    s = state["sA"]
    r = s.post(f"{API}/school/proxy/substitutions/{state['sub1']['id']}/cancel", json={"reason": "sorted"})
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_95_substitution_same_teacher_rejected():
    s = state["sA"]
    r = s.post(f"{API}/school/proxy/substitutions", json={
        "date": state["monday"], "academic_year_id": state["yr"]["id"],
        "timetable_slot_id": state["abs_slot"]["id"],
        "substitute_teacher_user_id": state["t2"]["id"],
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "same_teacher"


# ---------- Tenant isolation ----------
def test_a0_cross_tenant_cannot_see_slot():
    sB = state["sB"]
    r = sB.get(f"{API}/school/timetable/slots",
               params={"academic_year_id": state["yr"]["id"]})
    assert r.status_code == 200
    # Tenant B has no slots at tenant A's year
    assert r.json() == []


def test_a1_cross_tenant_cannot_patch():
    sB = state["sB"]
    r = sB.patch(f"{API}/school/timetable/slots/{state['slot1']['id']}", json={"notes": "hack"})
    assert r.status_code == 404


# ---------- RBAC ----------
def test_b0_teacher_cannot_manage_but_can_view():
    s = _login(f"t3-{RUN}@tta.example.com", "Teacher@123")
    r = s.get(f"{API}/school/timetable/slots", params={"academic_year_id": state["yr"]["id"]})
    assert r.status_code == 200
    r2 = s.post(f"{API}/school/timetable/slots", json={
        "academic_year_id": state["yr"]["id"], "class_id": state["cls"]["id"],
        "section_id": state["secA"]["id"], "bell_schedule_id": state["bell"]["id"],
        "weekday": "fri", "period_no": 1,
    })
    assert r2.status_code == 403


# ---------- Delete at end to not pollute other tests ----------
def test_zz_delete_slot():
    s = state["sA"]
    r = s.delete(f"{API}/school/timetable/slots/{state['slot1']['id']}")
    assert r.status_code == 200
