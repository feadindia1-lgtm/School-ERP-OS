"""Stabilization A+B edge cases: cross-section conflicts, lock, account-link guards. Also writes seed info for UI tests."""
import json
import os
import uuid

import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE}/api/v1"
RUN = uuid.uuid4().hex[:6]
EMAIL = f"owner-{RUN}@stab.example.com"
PW = "SchoolOwner@123"
st: dict = {}


def _det(r):
    b = r.json()
    return b.get("error", {}).get("details") or b.get("detail")


def _code(r):
    d = _det(r)
    return d.get("code") if isinstance(d, dict) else None


# --- bootstrap fresh school (slug test-stab-*) ---
def test_00_bootstrap():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/register-school", json={
        "school_name": f"Test Stab {RUN}", "slug": f"test-stab-{RUN}", "contact_email": EMAIL,
        "owner_full_name": "Stab Owner", "owner_email": EMAIL, "owner_password": PW})
    assert r.status_code == 201, r.text
    st["s"] = s
    y = s.post(f"{API}/school/academic/years", json={"name": f"Y{RUN}", "start_date": "2026-04-01", "end_date": "2027-03-31"}).json()
    c = s.post(f"{API}/school/academic/classes", json={"academic_year_id": y["id"], "name": "Class 5", "code": "5"}).json()
    sa = s.post(f"{API}/school/academic/sections", json={"academic_year_id": y["id"], "class_id": c["id"], "name": "A"}).json()
    sb = s.post(f"{API}/school/academic/sections", json={"academic_year_id": y["id"], "class_id": c["id"], "name": "B"}).json()
    sub = s.post(f"{API}/school/academic/subjects", json={"name": "Science", "code": "SCI"}).json()
    bell = s.post(f"{API}/school/academic/bell-schedules", json={
        "academic_year_id": y["id"], "name": "Regular", "is_default": False, "periods": [
            {"period_no": 1, "label": "P1", "start_time": "09:00", "end_time": "09:45"},
            {"period_no": 2, "label": "P2", "start_time": "09:45", "end_time": "10:30"},
            {"period_no": 3, "label": "Break", "start_time": "10:30", "end_time": "10:45", "is_break": True},
            {"period_no": 4, "label": "P3", "start_time": "10:45", "end_time": "11:30"},
        ]})
    assert bell.status_code == 201, bell.text
    room = s.post(f"{API}/school/academic/rooms", json={"name": "Room 1", "code": f"R{RUN}", "room_type": "classroom"})
    assert room.status_code == 201, room.text
    e1 = s.post(f"{API}/school/staff/employees", json={"first_name": "Meera", "last_name": "Sharma", "is_teaching_staff": True}).json()
    e2 = s.post(f"{API}/school/staff/employees", json={"first_name": "Ravi", "last_name": "Verma", "is_teaching_staff": True}).json()
    u1 = s.post(f"{API}/school/users", json={"email": f"meera.sharma{RUN}@stab.example.com", "full_name": "Meera Sharma",
                                             "password": "Teacher@123", "role": "teacher"})
    u2 = s.post(f"{API}/school/users", json={"email": f"ravi{RUN}@stab.example.com", "full_name": "Ravi V",
                                             "password": "Teacher@123", "role": "teacher"})
    assert u1.status_code == 201 and u2.status_code == 201
    st.update(y=y, c=c, sa=sa, sb=sb, sub=sub, bell=bell.json(), room=room.json(), e1=e1, e2=e2, u1=u1.json(), u2=u2.json())


def _slot(section, wd, pno, **kw):
    return st["s"].post(f"{API}/school/timetable/slots", json={
        "academic_year_id": st["y"]["id"], "class_id": st["c"]["id"], "section_id": section["id"],
        "bell_schedule_id": st["bell"]["id"], "weekday": wd, "period_no": pno, **kw})


# --- Workstream A: grid fallback + conflicts ---
def test_01_grid_fallback_no_default():
    g = st["s"].get(f"{API}/school/timetable/grid", params={"academic_year_id": st["y"]["id"], "section_id": st["sb"]["id"]}).json()
    assert g["bell_schedule"]["id"] == st["bell"]["id"]
    assert [p["period_no"] for p in g["bell_schedule"]["periods"]] == [1, 2, 3, 4]
    assert g["working_days"] == ["mon", "tue", "wed", "thu", "fri"]


def test_02_break_period_rejected():
    r = _slot(st["sa"], "mon", 3, subject_id=st["sub"]["id"])
    assert r.status_code == 409 and _code(r) == "period_is_break"


def test_03_teacher_and_room_double_book():
    r = _slot(st["sa"], "mon", 1, subject_id=st["sub"]["id"], teacher_user_id=st["u1"]["id"], room_id=st["room"]["id"])
    assert r.status_code == 201, r.text
    st["slotA"] = r.json()
    r2 = _slot(st["sb"], "mon", 1, subject_id=st["sub"]["id"], teacher_user_id=st["u1"]["id"], room_id=st["room"]["id"])
    assert r2.status_code == 409 and _code(r2) == "timetable_conflict"
    codes = {c["code"] for c in _det(r2)["conflicts"]}
    assert {"teacher_double_book", "room_double_book"} <= codes
    # validate endpoint (pre-save check used by cell editor)
    v = st["s"].post(f"{API}/school/timetable/validate", json={
        "academic_year_id": st["y"]["id"], "class_id": st["c"]["id"], "section_id": st["sb"]["id"],
        "bell_schedule_id": st["bell"]["id"], "weekday": "mon", "period_no": 1, "teacher_user_id": st["u1"]["id"]}).json()
    assert v["ok"] is False


def test_04_lock_blocks_edits():
    s = st["s"]; body = {"academic_year_id": st["y"]["id"], "section_id": st["sa"]["id"]}
    assert s.post(f"{API}/school/timetable/sections/lock", json={**body, "locked": True}).status_code == 200
    r = _slot(st["sa"], "tue", 1, subject_id=st["sub"]["id"])
    assert r.status_code == 409 and _code(r) == "timetable_locked"
    p = s.patch(f"{API}/school/timetable/slots/{st['slotA']['id']}", json={"label": "x"})
    assert p.status_code == 409
    d = s.delete(f"{API}/school/timetable/slots/{st['slotA']['id']}")
    assert d.status_code == 409
    s.post(f"{API}/school/timetable/sections/lock", json={**body, "locked": False})


def test_05_publish_then_patch_reverts_draft():
    s = st["s"]; body = {"academic_year_id": st["y"]["id"], "section_id": st["sa"]["id"]}
    p = s.post(f"{API}/school/timetable/sections/publish", json=body)
    assert p.status_code == 200, p.text
    assert p.json()["status"] == "published"
    s.patch(f"{API}/school/timetable/slots/{st['slotA']['id']}", json={"label": "Lab"})
    g = s.get(f"{API}/school/timetable/grid", params=body).json()
    assert g["meta"]["status"] == "draft" and g["meta"]["has_unpublished_changes"] is True


def test_06_grid_invalid_bell_id_param():
    r = st["s"].get(f"{API}/school/timetable/grid", params={"academic_year_id": st["y"]["id"], "section_id": st["sb"]["id"],
                                                          "bell_schedule_id": "not-an-id"})
    # Documenting behaviour: ideally falls back or 400
    st["invalid_bell_status"] = r.status_code
    assert r.status_code in (200, 400, 404, 422)


# --- Workstream B: account link guards ---
def test_07_suggestions_name_and_email():
    r = st["s"].get(f"{API}/school/staff/account-links").json()
    row = next(x for x in r["unlinked_employees"] if x["employee_id"] == st["e1"]["id"])
    assert row["suggestions"][0]["id"] == st["u1"]["id"]
    row2 = next(x for x in r["unlinked_employees"] if x["employee_id"] == st["e2"]["id"])
    assert row2["suggestions"] and row2["suggestions"][0]["id"] == st["u2"]["id"]
    # owner must never be suggested
    assert all(u["role"] != "school_owner" for u in r["unlinked_users"])


def test_08_link_backfills_slot_employee():
    s = st["s"]
    r = s.post(f"{API}/school/staff/employees/{st['e1']['id']}/account/link", json={"user_id": st["u1"]["id"]})
    assert r.status_code == 200, r.text
    slots = s.get(f"{API}/school/timetable/slots", params={"academic_year_id": st["y"]["id"], "section_id": st["sa"]["id"]}).json()
    assert next(x for x in slots if x["id"] == st["slotA"]["id"])["teacher_employee_id"] == st["e1"]["id"]
    dup = s.post(f"{API}/school/staff/employees/{st['e2']['id']}/account/link", json={"user_id": st["u1"]["id"]})
    assert dup.status_code == 409 and _code(dup) == "user_already_linked"


def test_09_create_login_guards():
    s = st["s"]; e = st["e2"]["id"]
    weak = s.post(f"{API}/school/staff/employees/{e}/account/create", json={"email": f"x{RUN}@stab.example.com", "password": "short"})
    assert weak.status_code in (400, 422)
    owner = s.post(f"{API}/school/staff/employees/{e}/account/create", json={"email": f"x{RUN}@stab.example.com",
                                                                             "password": "Teacher@123", "role": "school_owner"})
    assert owner.status_code == 400
    dup = s.post(f"{API}/school/staff/employees/{e}/account/create", json={"email": st["u1"]["email"].upper(), "password": "Teacher@123"})
    assert dup.status_code == 409 and _code(dup) == "email_in_use"


def test_10_link_invalid_user_id():
    r = st["s"].post(f"{API}/school/staff/employees/{st['e2']['id']}/account/link", json={"user_id": "bad"})
    st["invalid_link_status"] = r.status_code
    assert r.status_code in (400, 404, 422)


def test_99_write_seed():
    os.makedirs("/app/test_reports", exist_ok=True)
    with open("/app/test_reports/stab_seed.json", "w") as f:
        json.dump({"email": EMAIL, "password": PW, "year": st["y"]["id"], "class": st["c"]["id"],
                   "sa": st["sa"]["id"], "sb": st["sb"]["id"], "e1": st["e1"]["id"], "e2": st["e2"]["id"],
                   "e1_code": st["e1"].get("employee_code"), "e2_code": st["e2"].get("employee_code"),
                   "u1": st["u1"]["id"], "u2": st["u2"]["id"],
                   "invalid_bell_status": st.get("invalid_bell_status"), "invalid_link_status": st.get("invalid_link_status")}, f)
