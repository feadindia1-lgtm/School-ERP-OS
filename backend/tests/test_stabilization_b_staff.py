"""Stabilization Workstream B — Employee ↔ User ↔ TeacherAssignment linking."""
import os
import uuid

import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://schoolos-foundation-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"
RUN = uuid.uuid4().hex[:6]
EMAIL = f"owner-{RUN}@stb.example.com"
PW = "SchoolOwner@123"
st: dict = {}


def _code(r):
    b = r.json()
    d = b.get("error", {}).get("details") or b.get("detail")
    return d.get("code") if isinstance(d, dict) else None


def test_00_bootstrap():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/register-school", json={
        "school_name": f"STB {RUN}", "slug": f"stb-{RUN}", "contact_email": EMAIL,
        "owner_full_name": "Owner", "owner_email": EMAIL, "owner_password": PW})
    assert r.status_code == 201, r.text
    st["s"] = s
    y = s.post(f"{API}/school/academic/years", json={"name": f"Y{RUN}", "start_date": "2026-04-01", "end_date": "2027-03-31"}).json()
    c = s.post(f"{API}/school/academic/classes", json={"academic_year_id": y["id"], "name": "Class 2", "code": "2"}).json()
    st.update(y=y, c=c, sub=s.post(f"{API}/school/academic/subjects", json={"name": "English", "code": "EN"}).json())
    # Employee + an existing (unlinked) teacher login, created separately — the real-world gap
    st["emp"] = s.post(f"{API}/school/staff/employees", json={"first_name": "Gopesh", "last_name": "Kumar", "is_teaching_staff": True}).json()
    st["emp2"] = s.post(f"{API}/school/staff/employees", json={"first_name": "Rachna", "is_teaching_staff": True}).json()
    u = s.post(f"{API}/school/users", json={"email": f"gopesh{RUN}@stb.example.com", "full_name": "Gopesh K",
                                            "password": "Teacher@123", "role": "teacher"})
    assert u.status_code == 201, u.text
    st["u"] = u.json()
    a = s.post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": y["id"], "teacher_user_id": st["u"]["id"], "class_id": c["id"], "subject_id": st["sub"]["id"]})
    assert a.status_code == 201, a.text
    st["a"] = a.json()
    assert st["a"].get("employee_id") is None


def test_01_reconciliation_suggests_match():
    r = st["s"].get(f"{API}/school/staff/account-links")
    assert r.status_code == 200, r.text
    row = next(x for x in r.json()["unlinked_employees"] if x["employee_id"] == st["emp"]["id"])
    assert row["suggestions"] and row["suggestions"][0]["id"] == st["u"]["id"]
    acc = st["s"].get(f"{API}/school/staff/employees/{st['emp']['id']}/account").json()
    assert acc["linked_user"] is None and acc["default_role"] == "teacher"


def test_02_link_backfills_assignment():
    s = st["s"]
    r = s.post(f"{API}/school/staff/employees/{st['emp']['id']}/account/link", json={"user_id": st["u"]["id"]})
    assert r.status_code == 200, r.text
    a = s.get(f"{API}/school/academic/teacher-assignments", params={"academic_year_id": st["y"]["id"]}).json()
    assert next(x for x in a if x["id"] == st["a"]["id"])["employee_id"] == st["emp"]["id"]
    t = next(x for x in s.get(f"{API}/school/timetable/teachers").json() if x["id"] == st["u"]["id"])
    assert t["employee_id"] == st["emp"]["id"] and t["employee_code"] == st["emp"]["employee_code"]
    lst = s.get(f"{API}/school/staff/employees").json()["items"]
    assert next(x for x in lst if x["id"] == st["emp"]["id"])["linked_user"]["id"] == st["u"]["id"]


def test_03_link_is_idempotent_and_one_to_one():
    s = st["s"]
    again = s.post(f"{API}/school/staff/employees/{st['emp']['id']}/account/link", json={"user_id": st["u"]["id"]})
    assert again.status_code == 200
    dup = s.post(f"{API}/school/staff/employees/{st['emp2']['id']}/account/link", json={"user_id": st["u"]["id"]})
    assert dup.status_code == 409 and _code(dup) == "user_already_linked"
    patch = s.patch(f"{API}/school/staff/employees/{st['emp2']['id']}", json={"user_id": st["u"]["id"]})
    assert patch.status_code == 409


def test_04_create_login_from_employee():
    s = st["s"]
    r = s.post(f"{API}/school/staff/employees/{st['emp2']['id']}/account/create", json={
        "email": f"rachna{RUN}@stb.example.com", "password": "Teacher@123"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["role"] == "teacher" and body["user"]["full_name"] == "Rachna"
    st["u2"] = body["user"]
    # New login immediately available to Teacher Assignments
    a = s.post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": st["y"]["id"], "teacher_user_id": st["u2"]["id"], "class_id": st["c"]["id"]})
    assert a.status_code == 201, a.text
    assert a.json()["employee_id"] == st["emp2"]["id"]
    # Second create refused; no duplicate user
    again = s.post(f"{API}/school/staff/employees/{st['emp2']['id']}/account/create", json={
        "email": f"other{RUN}@stb.example.com", "password": "Teacher@123"})
    assert again.status_code == 409 and _code(again) == "employee_already_linked"


def test_05_create_with_existing_email_refused():
    s = st["s"]
    e3 = s.post(f"{API}/school/staff/employees", json={"first_name": "Third"}).json()
    r = s.post(f"{API}/school/staff/employees/{e3['id']}/account/create", json={
        "email": st["u"]["email"], "password": "Teacher@123"})
    assert r.status_code == 409 and _code(r) == "email_in_use"
    users = s.get(f"{API}/school/users").json()
    assert sum(1 for u in users if u["email"] == st["u"]["email"]) == 1


def test_06_new_login_can_sign_in():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": st["u2"]["email"], "password": "Teacher@123"})
    assert r.status_code == 200, r.text


def test_07_unlink_clears_employee_refs():
    s = st["s"]
    r = s.post(f"{API}/school/staff/employees/{st['emp2']['id']}/account/unlink")
    assert r.status_code == 200
    acc = s.get(f"{API}/school/staff/employees/{st['emp2']['id']}/account").json()
    assert acc["linked_user"] is None
    a = s.get(f"{API}/school/academic/teacher-assignments", params={"academic_year_id": st["y"]["id"]}).json()
    assert all(x.get("employee_id") is None for x in a if x["teacher_user_id"] == st["u2"]["id"])
    # Login is preserved
    assert any(u["id"] == st["u2"]["id"] for u in s.get(f"{API}/school/users").json())


def test_08_cross_tenant_isolation():
    s2 = requests.Session(); s2.headers.update({"Content-Type": "application/json"})
    e = f"o2-{RUN}@stb2.example.com"
    s2.post(f"{API}/auth/register-school", json={"school_name": f"STB2 {RUN}", "slug": f"stb2-{RUN}", "contact_email": e,
                                                  "owner_full_name": "Owner Two", "owner_email": e, "owner_password": PW})
    r = s2.get(f"{API}/school/staff/employees/{st['emp']['id']}/account")
    assert r.status_code == 404
    emp = s2.post(f"{API}/school/staff/employees", json={"first_name": "X"}).json()
    r2 = s2.post(f"{API}/school/staff/employees/{emp['id']}/account/link", json={"user_id": st["u"]["id"]})
    assert r2.status_code == 400
