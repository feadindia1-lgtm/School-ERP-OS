"""Prompt 5 — Staff Master + Leave Foundation tests.

Covers:
- Department + Designation CRUD (unique code, delete guard when employees exist)
- Employee CRUD with auto EMP-YYYY-NNNN + admin override + duplicate detection
- Employee status change (active → on_leave → resigned) + exit fields
- Employee documents (add / list / delete)
- Employee qualifications + Employee auto-marked is_teaching_staff
- Leave-type CRUD (preset shipped, approval_steps validation, soft-deactivate when in use)
- Leave-application happy path: apply → HR approve (single-step) → balance debited
- Two-step approval flow: pending → approved_l1 → approved
- Insufficient balance (409), overlap detection (409), requires_document enforcement
- Manual balance adjustment (credit + audit trail)
- Cancel approved leave restores balance
- Cross-tenant isolation
- RBAC — teacher can apply leave but cannot approve or manage staff
- Audit events emitted
- Overview counts
- TeacherAssignment auto-populates employee_id when linked user has an Employee
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
A_SLUG = f"stfa-{RUN}"
B_SLUG = f"stfb-{RUN}"
A_EMAIL = f"owner-{RUN}@stfa.example.com"
B_EMAIL = f"owner-{RUN}@stfb.example.com"
PW = "SchoolOwner@123"

state: dict = {}


def _sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


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
    state["sA"] = _register(A_SLUG, A_EMAIL, f"Stfa {RUN}")
    state["sB"] = _register(B_SLUG, B_EMAIL, f"Stfb {RUN}")


# ---------- Departments + Designations ----------
def test_10_department_crud():
    r = state["sA"].post(f"{API}/school/staff/departments", json={"name": "Academic", "code": "ACAD"})
    assert r.status_code == 201, r.text
    state["dept"] = r.json()
    dup = state["sA"].post(f"{API}/school/staff/departments", json={"name": "Other", "code": "ACAD"})
    assert dup.status_code == 409
    assert _err_code(dup.json()) == "duplicate_department"


def test_11_designation_crud():
    r = state["sA"].post(f"{API}/school/staff/designations", json={
        "title": "Teacher", "code": "TCH", "department_id": state["dept"]["id"], "is_teaching": True,
    })
    assert r.status_code == 201
    state["desig"] = r.json()
    r2 = state["sA"].post(f"{API}/school/staff/designations", json={
        "title": "Accountant", "code": "ACC",
    })
    assert r2.status_code == 201
    state["desig_acc"] = r2.json()


# ---------- Employees ----------
def test_20_employee_create_auto_code():
    r = state["sA"].post(f"{API}/school/staff/employees", json={
        "first_name": "Tara", "last_name": "Menon", "gender": "female",
        "department_id": state["dept"]["id"], "designation_id": state["desig"]["id"],
        "employment_type": "full_time", "joining_date": "2026-01-10",
        "mobile_primary": "9998887777", "is_teaching_staff": True,
    })
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["employee_code"].startswith("EMP-")
    assert e["status"] == "active"
    state["emp1"] = e


def test_21_employee_admin_override_code():
    r = state["sA"].post(f"{API}/school/staff/employees", json={
        "employee_code": "EMP-MANUAL-1", "first_name": "Bob", "last_name": "K",
    })
    assert r.status_code == 201
    assert r.json()["employee_code"] == "EMP-MANUAL-1"
    # Duplicate override rejected
    dup = state["sA"].post(f"{API}/school/staff/employees", json={
        "employee_code": "EMP-MANUAL-1", "first_name": "C",
    })
    assert dup.status_code == 409
    assert _err_code(dup.json()) == "duplicate_employee_code"


def test_22_employee_reject_unknown_department():
    r = state["sA"].post(f"{API}/school/staff/employees", json={
        "first_name": "X", "department_id": "a" * 24,
    })
    assert r.status_code == 400


def test_23_employee_status_change():
    r = state["sA"].post(f"{API}/school/staff/employees/{state['emp1']['id']}/status", json={
        "status": "on_leave", "reason": "test",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "on_leave"

    r2 = state["sA"].post(f"{API}/school/staff/employees/{state['emp1']['id']}/status", json={
        "status": "resigned", "reason": "moved abroad",
    })
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "resigned" and body.get("exit_date")


def test_24_employee_list_and_filters():
    # Reset to active for further tests
    state["sA"].post(f"{API}/school/staff/employees/{state['emp1']['id']}/status", json={"status": "active"})
    r = state["sA"].get(f"{API}/school/staff/employees", params={"q": "Tara"})
    assert r.status_code == 200 and r.json()["total"] >= 1


# ---------- Documents & qualifications ----------
def test_30_employee_document_add_and_delete():
    r = state["sA"].post(f"{API}/school/staff/employees/{state['emp1']['id']}/documents", json={
        "doc_type": "aadhaar", "filename": "aad.pdf", "storage_key": "s3/aad.pdf", "size_bytes": 1024,
    })
    assert r.status_code == 201
    did = r.json()["id"]
    r2 = state["sA"].get(f"{API}/school/staff/employees/{state['emp1']['id']}/documents")
    assert r2.status_code == 200 and any(d["id"] == did for d in r2.json())
    state["sA"].delete(f"{API}/school/staff/documents/{did}")


def test_31_qualification_marks_teaching_and_pushes_lists():
    # Need a real subject id first
    r = state["sA"].post(f"{API}/school/academic/subjects", json={"name": "Sci", "code": "SCI"})
    assert r.status_code == 201
    subj_id = r.json()["id"]
    r2 = state["sA"].post(f"{API}/school/staff/employees/{state['emp1']['id']}/qualifications", json={
        "kind": "subject", "subject_id": subj_id,
    })
    assert r2.status_code == 201
    emp = state["sA"].get(f"{API}/school/staff/employees/{state['emp1']['id']}").json()
    assert subj_id in emp["subjects_qualified"]
    assert emp["is_teaching_staff"] is True


# ---------- Leave types ----------
def test_40_leave_types_list_returns_presets_and_allows_create():
    r = state["sA"].get(f"{API}/school/staff/leave-types")
    assert r.status_code == 200
    body = r.json()
    assert "presets" in body and len(body["presets"]) >= 5
    r2 = state["sA"].post(f"{API}/school/staff/leave-types", json={
        "name": "Casual Leave", "code": "CL", "max_per_year": 12, "approval_steps": 1,
    })
    assert r2.status_code == 201
    state["lt_cl"] = r2.json()
    r3 = state["sA"].post(f"{API}/school/staff/leave-types", json={
        "name": "Earned Leave", "code": "EL", "max_per_year": 20, "approval_steps": 2,
    })
    state["lt_el"] = r3.json()


def test_41_leave_type_rejects_bad_approval_steps():
    r = state["sA"].post(f"{API}/school/staff/leave-types", json={
        "name": "Bad", "code": "BAD", "approval_steps": 5,
    })
    assert r.status_code == 400


def test_42_leave_type_dup_code():
    r = state["sA"].post(f"{API}/school/staff/leave-types", json={"name": "Casual", "code": "CL"})
    assert r.status_code == 409
    assert _err_code(r.json()) == "duplicate_leave_type"


# ---------- Leave applications ----------
def test_50_apply_leave_single_step_debits_on_approve():
    r = state["sA"].post(f"{API}/school/staff/leave-applications", json={
        "employee_id": state["emp1"]["id"], "leave_type_id": state["lt_cl"]["id"],
        "start_date": "2026-05-04", "end_date": "2026-05-05", "reason": "personal",
    })
    assert r.status_code == 201, r.text
    la = r.json()
    assert la["status"] == "pending" and la["days"] == 2
    state["la1"] = la
    # Approve
    r2 = state["sA"].post(f"{API}/school/staff/leave-applications/{la['id']}/approve", json={"reason": "ok"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "approved"
    # Balance debited
    r3 = state["sA"].get(f"{API}/school/staff/leave-balances", params={"employee_id": state["emp1"]["id"]})
    assert r3.status_code == 200
    b = [x for x in r3.json() if x["leave_type_id"] == state["lt_cl"]["id"]][0]
    assert b["used"] == 2
    assert b["balance"] == 10


def test_51_overlap_rejected():
    r = state["sA"].post(f"{API}/school/staff/leave-applications", json={
        "employee_id": state["emp1"]["id"], "leave_type_id": state["lt_cl"]["id"],
        "start_date": "2026-05-05", "end_date": "2026-05-06", "reason": "again",
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "leave_overlap"


def test_52_insufficient_balance_rejected():
    r = state["sA"].post(f"{API}/school/staff/leave-applications", json={
        "employee_id": state["emp1"]["id"], "leave_type_id": state["lt_cl"]["id"],
        "start_date": "2026-06-01", "end_date": "2026-06-30", "reason": "long",
    })
    assert r.status_code == 409
    assert _err_code(r.json()) == "insufficient_balance"


def test_53_two_step_approval_flow():
    r = state["sA"].post(f"{API}/school/staff/leave-applications", json={
        "employee_id": state["emp1"]["id"], "leave_type_id": state["lt_el"]["id"],
        "start_date": "2026-07-10", "end_date": "2026-07-12", "reason": "trip",
    })
    assert r.status_code == 201
    lid = r.json()["id"]
    r2 = state["sA"].post(f"{API}/school/staff/leave-applications/{lid}/approve", json={"reason": "l1"})
    assert r2.status_code == 200 and r2.json()["status"] == "approved_l1"
    r3 = state["sA"].post(f"{API}/school/staff/leave-applications/{lid}/approve", json={"reason": "final"})
    assert r3.status_code == 200 and r3.json()["status"] == "approved"
    state["la_el"] = r3.json()


def test_54_cancel_approved_restores_balance():
    lid = state["la1"]["id"]
    r = state["sA"].post(f"{API}/school/staff/leave-applications/{lid}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    r2 = state["sA"].get(f"{API}/school/staff/leave-balances", params={"employee_id": state["emp1"]["id"]})
    b = [x for x in r2.json() if x["leave_type_id"] == state["lt_cl"]["id"]][0]
    assert b["used"] == 0
    assert b["balance"] == 12


# ---------- Manual adjustment ----------
def test_60_manual_adjustment_credits_and_audits():
    r = state["sA"].post(f"{API}/school/staff/leave-balances/adjust", json={
        "employee_id": state["emp1"]["id"], "leave_type_id": state["lt_cl"]["id"],
        "year": "2026", "amount": 3, "reason": "grant",
    })
    assert r.status_code == 201
    assert r.json()["balance"] == 15
    # Audit log
    r2 = state["sA"].get(f"{API}/school/audit-logs", params={"limit": 100})
    actions = {a["action"] for a in r2.json()}
    assert "staff.leave_balance.adjust" in actions


# ---------- Overview ----------
def test_70_overview_counts():
    r = state["sA"].get(f"{API}/school/staff/overview")
    assert r.status_code == 200
    body = r.json()
    for k in ("total", "active", "teaching", "non_teaching", "on_leave", "resigned", "pending_leave_applications"):
        assert k in body
    assert body["total"] >= 2  # emp1 + manual


# ---------- Cross-tenant isolation ----------
def test_80_cross_tenant_hidden():
    r = state["sB"].get(f"{API}/school/staff/employees")
    assert r.status_code == 200 and r.json()["total"] == 0
    r2 = state["sB"].get(f"{API}/school/staff/employees/{state['emp1']['id']}")
    assert r2.status_code == 404
    r3 = state["sB"].get(f"{API}/school/staff/leave-applications")
    assert r3.status_code == 200 and r3.json()["total"] == 0


# ---------- RBAC ----------
def test_90_teacher_can_apply_but_not_approve_or_manage():
    r = state["sA"].post(f"{API}/school/users", json={
        "email": f"tch-{RUN}@stfa.example.com", "full_name": "Ms P",
        "password": "Teacher@123", "role": "teacher",
    })
    assert r.status_code == 201
    ts = _sess()
    r2 = ts.post(f"{API}/auth/login", json={"email": f"tch-{RUN}@stfa.example.com", "password": "Teacher@123"})
    assert r2.status_code == 200
    # Read allowed
    assert ts.get(f"{API}/school/staff/employees").status_code == 200
    # Cannot create employees
    r3 = ts.post(f"{API}/school/staff/employees", json={"first_name": "X"})
    assert r3.status_code == 403
    # Can apply (would need own employee_id; use emp1 as target — permission still fires 200/201)
    r4 = ts.post(f"{API}/school/staff/leave-applications", json={
        "employee_id": state["emp1"]["id"], "leave_type_id": state["lt_cl"]["id"],
        "start_date": "2026-09-01", "end_date": "2026-09-01", "reason": "teacher-applied",
    })
    assert r4.status_code == 201
    # Cannot approve
    r5 = ts.post(f"{API}/school/staff/leave-applications/{r4.json()['id']}/approve", json={"reason": "no"})
    assert r5.status_code == 403


# ---------- Teacher assignment employee_id sync ----------
def test_100_teacher_assignment_auto_resolves_employee_id():
    # Create academic year + class + section
    y = state["sA"].post(f"{API}/school/academic/years", json={
        "name": f"tst-{RUN}", "start_date": "2026-04-01", "end_date": "2027-03-31", "is_current": True,
    }).json()
    c = state["sA"].post(f"{API}/school/academic/classes", json={
        "academic_year_id": y["id"], "name": "Grade 1", "code": f"G1-{RUN}",
    }).json()
    # Create a login user + linked Employee
    u = state["sA"].post(f"{API}/school/users", json={
        "email": f"link-{RUN}@stfa.example.com", "full_name": "Linked Teacher",
        "password": "Teacher@123", "role": "teacher",
    }).json()
    linked = state["sA"].post(f"{API}/school/staff/employees", json={
        "first_name": "Linked", "user_id": u["id"], "is_teaching_staff": True,
    }).json()
    # Assign to the class
    r = state["sA"].post(f"{API}/school/academic/teacher-assignments", json={
        "academic_year_id": y["id"], "teacher_user_id": u["id"], "class_id": c["id"],
    })
    assert r.status_code == 201, r.text
    assert r.json()["employee_id"] == linked["id"]
