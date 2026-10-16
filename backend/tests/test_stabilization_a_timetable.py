"""Stabilization Workstream A — master timetable grid + draft/validate/publish lifecycle."""
import os
import uuid

import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://schoolos-foundation-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"
RUN = uuid.uuid4().hex[:6]
EMAIL = f"owner-{RUN}@sta.example.com"
PW = "SchoolOwner@123"
st: dict = {}


def _code(r):
    b = r.json()
    d = b.get("error", {}).get("details") or b.get("detail")
    return d.get("code") if isinstance(d, dict) else None


def _details(r):
    b = r.json()
    return b.get("error", {}).get("details") or b.get("detail")


def test_00_bootstrap():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/register-school", json={
        "school_name": f"STA {RUN}", "slug": f"sta-{RUN}", "contact_email": EMAIL,
        "owner_full_name": "Owner", "owner_email": EMAIL, "owner_password": PW})
    assert r.status_code == 201, r.text
    st["s"] = s
    y = s.post(f"{API}/school/academic/years", json={"name": f"Y{RUN}", "start_date": "2026-04-01", "end_date": "2027-03-31"}).json()
    st["y"] = y
    c = s.post(f"{API}/school/academic/classes", json={"academic_year_id": y["id"], "name": "Class 1", "code": "1"}).json()
    st["c"] = c
    st["sec"] = s.post(f"{API}/school/academic/sections", json={"academic_year_id": y["id"], "class_id": c["id"], "name": "A"}).json()
    st["sec2"] = s.post(f"{API}/school/academic/sections", json={"academic_year_id": y["id"], "class_id": c["id"], "name": "B"}).json()
    st["math"] = s.post(f"{API}/school/academic/subjects", json={"name": "Maths", "code": "M"}).json()
    # Two bell schedules, neither marked default (reproduces the empty-grid bug)
    st["bell"] = s.post(f"{API}/school/academic/bell-schedules", json={
        "academic_year_id": y["id"], "name": "Weekday", "is_default": False, "periods": [
            {"period_no": 1, "label": "P1", "start_time": "09:00", "end_time": "09:45"},
            {"period_no": 2, "label": "Break", "start_time": "09:45", "end_time": "10:00", "is_break": True},
            {"period_no": 3, "label": "P2", "start_time": "10:00", "end_time": "10:45"},
        ]}).json()
    st["bell_short"] = s.post(f"{API}/school/academic/bell-schedules", json={
        "academic_year_id": y["id"], "name": "Half", "is_default": False, "periods": [
            {"period_no": 1, "label": "P1", "start_time": "09:00", "end_time": "09:45"},
        ]}).json()
    t = s.post(f"{API}/school/users", json={"email": f"t-{RUN}@sta.example.com", "full_name": "Tea Cher",
                                            "password": "Teacher@123", "role": "teacher"})
    assert t.status_code == 201, t.text
    st["t"] = t.json()


def test_01_grid_renders_periods_without_default_bell():
    s = st["s"]
    r = s.get(f"{API}/school/timetable/grid", params={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]})
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["bell_schedule"] is not None
    assert g["bell_schedule"]["id"] == st["bell"]["id"]
    assert [p["period_no"] for p in g["bell_schedule"]["periods"]] == [1, 2, 3]
    assert g["teacher_assignments"] == []


def test_02_grid_honours_requested_bell():
    s = st["s"]
    r = s.get(f"{API}/school/timetable/grid", params={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"],
                                                     "bell_schedule_id": st["bell_short"]["id"]})
    assert r.json()["bell_schedule"]["id"] == st["bell_short"]["id"]


def test_03_teacher_picker_lists_login_teachers():
    r = st["s"].get(f"{API}/school/timetable/teachers")
    assert r.status_code == 200
    row = next(x for x in r.json() if x["id"] == st["t"]["id"])
    assert row["employee_id"] is None


def test_04_set_bell_and_validate_empty():
    s = st["s"]
    r = s.post(f"{API}/school/timetable/sections/bell", json={
        "academic_year_id": st["y"]["id"], "class_id": st["c"]["id"], "section_id": st["sec"]["id"],
        "bell_schedule_id": st["bell"]["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "draft"
    v = s.post(f"{API}/school/timetable/sections/validate", json={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]}).json()
    assert v["ok"] is False and any(e["code"] == "empty_timetable" for e in v["errors"])
    p = s.post(f"{API}/school/timetable/sections/publish", json={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]})
    assert p.status_code == 409 and _code(p) == "empty_timetable"


def test_05_slot_draft_validate_publish():
    s = st["s"]
    r = s.post(f"{API}/school/timetable/slots", json={
        "academic_year_id": st["y"]["id"], "class_id": st["c"]["id"], "section_id": st["sec"]["id"],
        "bell_schedule_id": st["bell"]["id"], "weekday": "mon", "period_no": 1,
        "subject_id": st["math"]["id"], "teacher_user_id": st["t"]["id"]})
    assert r.status_code == 201, r.text
    st["slot"] = r.json()
    v = s.post(f"{API}/school/timetable/sections/validate", json={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]}).json()
    assert v["ok"] is True
    codes = {w["code"] for w in v["warnings"]}
    assert "teacher_not_assigned" in codes and "empty_cells" in codes
    p = s.post(f"{API}/school/timetable/sections/publish", json={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]})
    assert p.status_code == 200, p.text
    assert p.json()["status"] == "published" and p.json()["version"] == 1
    assert p.json()["has_unpublished_changes"] is False


def test_06_assignment_clears_warning():
    s = st["s"]
    a = s.post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": st["y"]["id"], "teacher_user_id": st["t"]["id"], "class_id": st["c"]["id"],
        "section_id": st["sec"]["id"], "subject_id": st["math"]["id"]})
    assert a.status_code == 201, a.text
    v = s.post(f"{API}/school/timetable/sections/validate", json={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]}).json()
    assert "teacher_not_assigned" not in {w["code"] for w in v["warnings"]}
    g = s.get(f"{API}/school/timetable/grid", params={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]}).json()
    assert len(g["teacher_assignments"]) == 1


def test_07_edit_returns_to_draft():
    s = st["s"]
    r = s.post(f"{API}/school/timetable/slots", json={
        "academic_year_id": st["y"]["id"], "class_id": st["c"]["id"], "section_id": st["sec"]["id"],
        "bell_schedule_id": st["bell"]["id"], "weekday": "tue", "period_no": 3, "label": "Library"})
    assert r.status_code == 201
    g = s.get(f"{API}/school/timetable/grid", params={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]}).json()
    assert g["meta"]["status"] == "draft" and g["meta"]["has_unpublished_changes"] is True
    assert g["meta"]["published_at"]


def test_08_incompatible_bell_rejected():
    r = st["s"].post(f"{API}/school/timetable/sections/bell", json={
        "academic_year_id": st["y"]["id"], "class_id": st["c"]["id"], "section_id": st["sec"]["id"],
        "bell_schedule_id": st["bell_short"]["id"]})
    assert r.status_code == 409 and _code(r) == "bell_incompatible"


def test_09_disabled_teacher_blocks_publish():
    s = st["s"]
    u = s.patch(f"{API}/school/users/{st['t']['id']}", json={"status": "disabled"})
    assert u.status_code == 200, u.text
    p = s.post(f"{API}/school/timetable/sections/publish", json={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]})
    assert p.status_code == 409 and _code(p) == "validation_failed"
    assert any(e["code"] == "teacher_inactive" for e in _details(p)["errors"])
    s.patch(f"{API}/school/users/{st['t']['id']}", json={"status": "active"})
    p2 = s.post(f"{API}/school/timetable/sections/publish", json={"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]})
    assert p2.status_code == 200 and p2.json()["version"] == 2


def test_10_locked_cannot_publish():
    s = st["s"]
    body = {"academic_year_id": st["y"]["id"], "section_id": st["sec"]["id"]}
    s.post(f"{API}/school/timetable/sections/lock", json={**body, "locked": True})
    p = s.post(f"{API}/school/timetable/sections/publish", json=body)
    assert p.status_code == 409 and _code(p) == "timetable_locked"
    s.post(f"{API}/school/timetable/sections/lock", json={**body, "locked": False})
