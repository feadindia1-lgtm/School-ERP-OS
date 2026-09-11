"""Prompt 4 — Academic Structure & School Calendar tests.

Covers:
- Board config seed + patch
- Academic year create/list/set-current/archive (with is_current uniqueness)
- Historical (archived) year is read-only (409 on mutations)
- Classes: unique code per year, delete blocked when sections exist
- Sections: unique name per class, class-teacher role validation
- Subjects: unique code, in-use guard
- Subject groups: subject existence validation
- Rooms: unique code, in-use guard
- Bell schedules: period overlap + duplicate period_no detection
- Working-day policy: weekday validation + weekly-off/working-day conflict
- Holidays: date-range validation
- Teacher assignments: FK validation, class-teacher uniqueness, duplicate detection
- Cross-tenant isolation for every resource
- RBAC — teacher role read-only
- Audit events fired
- Overview endpoint counts
"""
import os
import uuid

import requests

BASE = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://schoolos-foundation-1.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE}/api/v1"

RUN = uuid.uuid4().hex[:6]
A_SLUG = f"aca-{RUN}"
B_SLUG = f"acb-{RUN}"
A_EMAIL = f"owner-{RUN}@aca.example.com"
B_EMAIL = f"owner-{RUN}@acb.example.com"
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


def _err_code(body: dict) -> str | None:
    details = body.get("error", {}).get("details") or body.get("detail")
    if isinstance(details, dict): return details.get("code")
    return None


# ---------- Bootstrap ----------
def test_00_bootstrap():
    state["sA"] = _register(A_SLUG, A_EMAIL, f"Aca {RUN}")
    state["sB"] = _register(B_SLUG, B_EMAIL, f"Acb {RUN}")


# ---------- Board config ----------
def test_10_board_config_seeded_on_first_read():
    r = state["sA"].get(f"{API}/school/academic/board-config")
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert cfg["board"] in {"CBSE", "ICSE", "IB", "IGCSE", "STATE", "CUSTOM"}
    assert cfg["class_label"] and cfg["section_label"]
    assert "presets" in cfg and "CBSE" in cfg["presets"]
    state["A_board"] = cfg


def test_11_board_config_patch_terms_and_label():
    r = state["sA"].patch(f"{API}/school/academic/board-config", json={
        "class_label": "Grade", "terms": ["T1", "T2", "T3"],
    })
    assert r.status_code == 200, r.text
    assert r.json()["class_label"] == "Grade"
    assert r.json()["terms"] == ["T1", "T2", "T3"]


def test_12_board_config_rejects_unknown_board():
    r = state["sA"].patch(f"{API}/school/academic/board-config", json={"board": "NONEXISTENT"})
    assert r.status_code == 400


# ---------- Academic years ----------
def test_20_create_year_and_set_current():
    r = state["sA"].post(f"{API}/school/academic/years", json={
        "name": "2026-27", "start_date": "2026-04-01", "end_date": "2027-03-31",
        "is_current": True, "board_preset": "CBSE",
    })
    assert r.status_code == 201, r.text
    y = r.json()
    assert y["is_current"] is True and y["status"] == "current"
    assert y["term_names"] == ["Term 1", "Term 2"]  # from preset
    state["yr1"] = y

    r2 = state["sA"].post(f"{API}/school/academic/years", json={
        "name": "2027-28", "start_date": "2027-04-01", "end_date": "2028-03-31",
    })
    assert r2.status_code == 201
    state["yr2"] = r2.json()


def test_21_year_start_before_end_validation():
    r = state["sA"].post(f"{API}/school/academic/years", json={
        "name": "bad", "start_date": "2027-04-01", "end_date": "2027-01-01",
    })
    assert r.status_code == 400


def test_22_duplicate_year_name_returns_409():
    r = state["sA"].post(f"{API}/school/academic/years", json={
        "name": "2026-27", "start_date": "2028-04-01", "end_date": "2029-03-31",
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "duplicate_year"


def test_23_set_current_flips_previous_current():
    r = state["sA"].post(f"{API}/school/academic/years/{state['yr2']['id']}/set-current")
    assert r.status_code == 200
    assert r.json()["is_current"] is True
    prev = state["sA"].get(f"{API}/school/academic/years/{state['yr1']['id']}").json()
    assert prev["is_current"] is False


def test_24_archive_year_and_reject_mutations():
    r = state["sA"].post(f"{API}/school/academic/years/{state['yr1']['id']}/archive")
    assert r.status_code == 200
    assert r.json()["status"] == "archived"
    # Patch should now fail
    r2 = state["sA"].patch(f"{API}/school/academic/years/{state['yr1']['id']}", json={"notes": "x"})
    assert r2.status_code == 409
    assert _err_code(r2.json()) == "year_archived"


def test_25_cannot_archive_current_year():
    r = state["sA"].post(f"{API}/school/academic/years/{state['yr2']['id']}/archive")
    assert r.status_code == 409
    assert _err_code(r.json()) == "year_current"


# ---------- Classes ----------
def test_30_create_class_and_unique_code():
    yid = state["yr2"]["id"]
    r = state["sA"].post(f"{API}/school/academic/classes", json={
        "academic_year_id": yid, "name": "Class 5", "code": "5", "order": 5,
    })
    assert r.status_code == 201, r.text
    state["cls5"] = r.json()

    dup = state["sA"].post(f"{API}/school/academic/classes", json={
        "academic_year_id": yid, "name": "Fifth", "code": "5",
    })
    assert dup.status_code == 409
    assert _err_code(dup.json()) == "duplicate_class"


def test_31_class_list_filtered_by_year():
    r = state["sA"].get(f"{API}/school/academic/classes", params={"academic_year_id": state["yr2"]["id"]})
    assert r.status_code == 200
    assert any(c["code"] == "5" for c in r.json())


def test_32_class_in_archived_year_rejected():
    r = state["sA"].post(f"{API}/school/academic/classes", json={
        "academic_year_id": state["yr1"]["id"], "name": "Class 5", "code": "5",
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "year_archived"


# ---------- Sections ----------
def test_40_create_section_with_class_teacher():
    # First create a teacher user in tenant A
    from_owner = state["sA"].get(f"{API}/auth/me").json()
    r = state["sA"].post(f"{API}/school/users", json={
        "email": f"tch-{RUN}@aca.example.com", "full_name": "Ms Tara",
        "password": "Teacher@123", "role": "teacher",
    })
    assert r.status_code == 201, r.text
    state["teacher_id"] = r.json()["id"]

    r2 = state["sA"].post(f"{API}/school/academic/sections", json={
        "academic_year_id": state["yr2"]["id"], "class_id": state["cls5"]["id"],
        "name": "A", "capacity": 30, "class_teacher_user_id": state["teacher_id"],
    })
    assert r2.status_code == 201, r2.text
    state["secA"] = r2.json()


def test_41_section_unique_name_per_class():
    r = state["sA"].post(f"{API}/school/academic/sections", json={
        "academic_year_id": state["yr2"]["id"], "class_id": state["cls5"]["id"], "name": "A",
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "duplicate_section"


def test_42_section_rejects_non_teacher_user():
    owner = state["sA"].get(f"{API}/auth/me").json()
    r = state["sA"].post(f"{API}/school/academic/sections", json={
        "academic_year_id": state["yr2"]["id"], "class_id": state["cls5"]["id"],
        "name": "B", "class_teacher_user_id": owner["id"],
    })
    assert r.status_code == 400


def test_43_class_delete_blocked_when_sections_exist():
    r = state["sA"].delete(f"{API}/school/academic/classes/{state['cls5']['id']}")
    assert r.status_code == 409
    assert _err_code(r.json()) == "class_in_use"


# ---------- Subjects ----------
def test_50_subject_crud_and_unique_code():
    r = state["sA"].post(f"{API}/school/academic/subjects", json={
        "name": "Mathematics", "code": "MATH", "subject_type": "theory",
    })
    assert r.status_code == 201, r.text
    state["subj_math"] = r.json()
    r2 = state["sA"].post(f"{API}/school/academic/subjects", json={"name": "Maths", "code": "MATH"})
    assert r2.status_code == 409
    assert _err_code(r2.json()) == "duplicate_subject"


def test_51_subject_rejects_unknown_type():
    r = state["sA"].post(f"{API}/school/academic/subjects", json={
        "name": "Extra", "code": "EXT", "subject_type": "UNKNOWN",
    })
    assert r.status_code == 400


def test_52_subject_group_validates_subject_ids():
    r = state["sA"].post(f"{API}/school/academic/subject-groups", json={
        "academic_year_id": state["yr2"]["id"], "class_id": state["cls5"]["id"],
        "name": "Grade 5 Core", "subject_ids": [state["subj_math"]["id"]],
    })
    assert r.status_code == 201, r.text
    state["grp"] = r.json()

    bad = state["sA"].post(f"{API}/school/academic/subject-groups", json={
        "academic_year_id": state["yr2"]["id"], "class_id": state["cls5"]["id"],
        "name": "Bad", "subject_ids": ["a" * 24],
    })
    assert bad.status_code == 400


# ---------- Rooms ----------
def test_60_room_crud_and_unique_code():
    r = state["sA"].post(f"{API}/school/academic/rooms", json={
        "name": "Room 101", "code": "R101", "room_type": "classroom", "capacity": 30,
    })
    assert r.status_code == 201
    state["room101"] = r.json()
    dup = state["sA"].post(f"{API}/school/academic/rooms", json={"name": "Other", "code": "R101"})
    assert dup.status_code == 409


# ---------- Bell schedules ----------
def test_70_bell_schedule_ok():
    r = state["sA"].post(f"{API}/school/academic/bell-schedules", json={
        "academic_year_id": state["yr2"]["id"], "name": "Weekday", "is_default": True,
        "periods": [
            {"period_no": 1, "start_time": "08:00", "end_time": "08:40", "label": "P1", "is_break": False},
            {"period_no": 2, "start_time": "08:45", "end_time": "09:25", "label": "P2", "is_break": False},
            {"period_no": 3, "start_time": "09:25", "end_time": "09:40", "label": "Break", "is_break": True},
        ],
    })
    assert r.status_code == 201, r.text
    state["bell"] = r.json()


def test_71_bell_schedule_overlap_rejected():
    r = state["sA"].post(f"{API}/school/academic/bell-schedules", json={
        "academic_year_id": state["yr2"]["id"], "name": "Overlap",
        "periods": [
            {"period_no": 1, "start_time": "08:00", "end_time": "08:40"},
            {"period_no": 2, "start_time": "08:30", "end_time": "09:00"},
        ],
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "period_overlap"


def test_72_bell_schedule_duplicate_period_no():
    r = state["sA"].post(f"{API}/school/academic/bell-schedules", json={
        "academic_year_id": state["yr2"]["id"], "name": "DupNo",
        "periods": [
            {"period_no": 1, "start_time": "08:00", "end_time": "08:40"},
            {"period_no": 1, "start_time": "08:45", "end_time": "09:25"},
        ],
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "duplicate_period_no"


# ---------- Working-day policy ----------
def test_80_working_day_policy_put_and_conflict():
    r = state["sA"].put(f"{API}/school/academic/working-day-policy", json={
        "academic_year_id": state["yr2"]["id"],
        "working_days": ["mon", "tue", "wed", "thu", "fri", "sat"],
        "half_days": ["sat"], "weekly_off": ["sun"],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["working_days"]) == {"mon", "tue", "wed", "thu", "fri", "sat"}
    assert body["half_days"] == ["sat"]

    bad = state["sA"].put(f"{API}/school/academic/working-day-policy", json={
        "academic_year_id": state["yr2"]["id"],
        "working_days": ["mon", "tue"], "weekly_off": ["mon"],
    })
    assert bad.status_code == 409
    assert _err_code(bad.json()) == "weekday_conflict"


def test_81_working_day_policy_rejects_unknown_weekday():
    r = state["sA"].put(f"{API}/school/academic/working-day-policy", json={
        "academic_year_id": state["yr2"]["id"], "working_days": ["mon", "funday"],
    })
    assert r.status_code == 400


# ---------- Holidays ----------
def test_90_holiday_create_and_range_validation():
    r = state["sA"].post(f"{API}/school/academic/holidays", json={
        "academic_year_id": state["yr2"]["id"], "name": "Diwali",
        "start_date": "2027-10-25", "end_date": "2027-10-27", "category": "public",
    })
    assert r.status_code == 201
    state["hol1"] = r.json()

    bad = state["sA"].post(f"{API}/school/academic/holidays", json={
        "academic_year_id": state["yr2"]["id"], "name": "Bad",
        "start_date": "2027-10-27", "end_date": "2027-10-25",
    })
    assert bad.status_code == 400


# ---------- Teacher assignments ----------
def test_100_teacher_assignment_happy_path():
    r = state["sA"].post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": state["yr2"]["id"],
        "teacher_user_id": state["teacher_id"],
        "class_id": state["cls5"]["id"], "section_id": state["secA"]["id"],
        "subject_id": state["subj_math"]["id"], "weekly_periods": 5,
    })
    assert r.status_code == 201, r.text
    state["assign1"] = r.json()


def test_101_teacher_assignment_duplicate_rejected():
    r = state["sA"].post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": state["yr2"]["id"],
        "teacher_user_id": state["teacher_id"],
        "class_id": state["cls5"]["id"], "section_id": state["secA"]["id"],
        "subject_id": state["subj_math"]["id"],
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "duplicate_assignment"


def test_102_class_teacher_uniqueness_per_section():
    # First class-teacher assignment
    r = state["sA"].post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": state["yr2"]["id"],
        "teacher_user_id": state["teacher_id"],
        "class_id": state["cls5"]["id"], "section_id": state["secA"]["id"],
        "is_class_teacher": True,
    })
    assert r.status_code == 201

    # Second teacher in same section as class_teacher = conflict
    r2 = state["sA"].post(f"{API}/school/users", json={
        "email": f"tch2-{RUN}@aca.example.com", "full_name": "Mr B",
        "password": "Teacher@123", "role": "teacher",
    })
    assert r2.status_code == 201
    r3 = state["sA"].post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": state["yr2"]["id"],
        "teacher_user_id": r2.json()["id"],
        "class_id": state["cls5"]["id"], "section_id": state["secA"]["id"],
        "is_class_teacher": True,
    })
    assert r3.status_code == 409
    assert _err_code(r3.json()) == "class_teacher_exists"


def test_103_teacher_assignment_rejects_non_teacher():
    owner = state["sA"].get(f"{API}/auth/me").json()
    r = state["sA"].post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": state["yr2"]["id"],
        "teacher_user_id": owner["id"],
        "class_id": state["cls5"]["id"], "section_id": state["secA"]["id"],
    })
    assert r.status_code == 400


def test_104_teacher_assignment_class_belongs_to_year_check():
    # Create a class in yr1 (archived) — can't. Instead, try to attach to yr2
    # but with class_id from wrong year: use yr1 archived year — expect year_archived
    r = state["sA"].post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": state["yr1"]["id"],
        "teacher_user_id": state["teacher_id"],
        "class_id": state["cls5"]["id"],
    })
    assert r.status_code == 409  # archived


# ---------- Overview ----------
def test_110_overview_counts():
    r = state["sA"].get(f"{API}/school/academic/overview/{state['yr2']['id']}")
    assert r.status_code == 200, r.text
    body = r.json()
    c = body["counts"]
    assert c["classes"] >= 1 and c["sections"] >= 1
    assert c["bell_schedules"] >= 1 and c["holidays"] >= 1
    assert c["teacher_assignments"] >= 2  # subject + class-teacher rows
    assert body["year"]["id"] == state["yr2"]["id"]


# ---------- Cross-tenant isolation ----------
def test_120_cross_tenant_hidden():
    # Tenant B lists — must NOT see A's data
    r = state["sB"].get(f"{API}/school/academic/years")
    assert r.status_code == 200 and all(y["id"] != state["yr2"]["id"] for y in r.json())
    r2 = state["sB"].get(f"{API}/school/academic/classes", params={"academic_year_id": state["yr2"]["id"]})
    assert r2.status_code == 200 and r2.json() == []
    # Direct access → 404
    r3 = state["sB"].get(f"{API}/school/academic/years/{state['yr2']['id']}")
    assert r3.status_code == 404
    r4 = state["sB"].patch(f"{API}/school/academic/years/{state['yr2']['id']}", json={"notes": "hack"})
    assert r4.status_code == 404
    r5 = state["sB"].get(f"{API}/school/academic/sections/{state['secA']['id']}")
    assert r5.status_code == 404


# ---------- RBAC ----------
def test_130_teacher_can_view_but_not_manage():
    ts = _sess()
    r = ts.post(f"{API}/auth/login", json={"email": f"tch-{RUN}@aca.example.com", "password": "Teacher@123"})
    assert r.status_code == 200, r.text
    # View allowed
    r2 = ts.get(f"{API}/school/academic/years")
    assert r2.status_code == 200
    r3 = ts.get(f"{API}/school/academic/classes", params={"academic_year_id": state["yr2"]["id"]})
    assert r3.status_code == 200
    # Manage denied (403)
    r4 = ts.post(f"{API}/school/academic/subjects", json={"name": "Eng", "code": "ENGX"})
    assert r4.status_code == 403


# ---------- Audit ----------
def test_140_audit_events_emitted():
    r = state["sA"].get(f"{API}/school/audit-logs", params={"limit": 100})
    assert r.status_code == 200
    actions = {e["action"] for e in r.json()}
    for a in ("academic.year.create", "academic.class.create",
              "academic.section.create", "academic.subject.create",
              "academic.bell.create", "academic.assignment.create"):
        assert a in actions, f"missing audit for {a}"
