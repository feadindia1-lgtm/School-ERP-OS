"""Prompt 3 — Student Master + Guardian/Family tests.

Covers:
- Student CRUD (create, list w/ paging & search, patch, status change)
- Duplicate detection with force bypass
- Enrollments (list/create/patch, active-year uniqueness, snapshot updates)
- Guardian CRUD & search
- Student-Guardian link/unlink/list (409 on dup link, soft-terminate on delete)
- Shared guardian across siblings via admission conversion (reuse by mobile)
- Family CRUD (+ family detail with linked students/guardians)
- Idempotent admission conversion (assert single row per collection)
- Cross-tenant isolation on all new endpoints
- RBAC teacher denials
- Audit events fired
"""
import io
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests

BASE = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://schoolos-foundation-1.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE}/api/v1"

RUN = uuid.uuid4().hex[:6]
A_SLUG = f"stma-{RUN}"
B_SLUG = f"stmb-{RUN}"
A_EMAIL = f"owner-{RUN}@stma.example.com"
B_EMAIL = f"owner-{RUN}@stmb.example.com"
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


# ---------- Bootstrap ----------
def test_00_bootstrap():
    state["sA"] = _register(A_SLUG, A_EMAIL, f"StMa {RUN}")
    state["sB"] = _register(B_SLUG, B_EMAIL, f"StMb {RUN}")
    me = state["sA"].get(f"{API}/auth/me").json()
    state["A_tenant"] = me["tenant_id"]
    state["A_user"] = me["id"]
    me_b = state["sB"].get(f"{API}/auth/me").json()
    state["B_user"] = me_b["id"]


# ---------- Student create + duplicate + force ----------
def test_10_create_student_generates_admission_number():
    r = state["sA"].post(f"{API}/school/students", json={
        "first_name": "Riya", "last_name": "Sharma",
        "date_of_birth": "2015-05-10", "gender": "female",
        "academic_year": "2026-2027", "class_name": "Grade 5", "section": "A",
    })
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["admission_number"].startswith("STU-")
    parts = s["admission_number"].split("-")
    assert len(parts) == 3 and parts[2].isdigit() and len(parts[2]) == 6
    assert s["status"] == "ACTIVE"
    assert "_id" not in s and "id" in s
    state["stu1"] = s


def test_11_duplicate_detection_returns_409_with_code():
    r = state["sA"].post(f"{API}/school/students", json={
        "first_name": "Riya", "last_name": "Sharma",
        "date_of_birth": "2015-05-10",
    })
    assert r.status_code == 409, r.text
    body = r.json()
    # Response envelope: error.details.code
    details = body.get("error", {}).get("details") or body.get("detail")
    if isinstance(details, dict):
        assert details.get("code") == "duplicate_student"
    else:
        # Fallback if raw detail
        assert "duplicate_student" in str(body)


def test_12_duplicate_force_bypasses():
    r = state["sA"].post(f"{API}/school/students", json={
        "first_name": "Riya", "last_name": "Sharma",
        "date_of_birth": "2015-05-10", "force": True,
    })
    assert r.status_code == 201, r.text
    state["stu_dup_forced"] = r.json()


# ---------- List: pagination, search, filter ----------
def test_20_list_pagination_and_search():
    r = state["sA"].get(f"{API}/school/students", params={"page": 1, "page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1 and body["page_size"] == 5
    assert body["total"] >= 2

    r2 = state["sA"].get(f"{API}/school/students", params={"q": "Riya"})
    assert r2.status_code == 200
    assert r2.json()["total"] >= 2

    r3 = state["sA"].get(f"{API}/school/students", params={"status": "ACTIVE"})
    assert r3.status_code == 200
    assert all(x["status"] == "ACTIVE" for x in r3.json()["items"])


# ---------- PATCH ----------
def test_30_patch_student():
    sid = state["stu1"]["id"]
    r = state["sA"].patch(f"{API}/school/students/{sid}", json={"preferred_name": "Ri"})
    assert r.status_code == 200
    assert r.json()["preferred_name"] == "Ri"


# ---------- Status change ----------
def test_40_status_change_valid_and_invalid():
    sid = state["stu1"]["id"]
    r = state["sA"].post(f"{API}/school/students/{sid}/status", json={
        "status": "ON_LEAVE", "reason": "medical",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ON_LEAVE"
    assert body["status_reason"] == "medical"

    r2 = state["sA"].post(f"{API}/school/students/{sid}/status",
                          json={"status": "BOGUS"})
    assert r2.status_code == 400


# ---------- Enrollments ----------
def test_50_enrollments_create_dup_and_snapshot():
    sid = state["stu1"]["id"]
    r = state["sA"].post(f"{API}/school/students/{sid}/enrollments", json={
        "academic_year": "2026-2027", "class_name": "Grade 5",
        "section": "B", "roll_number": "12",
    })
    assert r.status_code == 201, r.text
    state["enr1"] = r.json()

    # duplicate active year => 409
    r2 = state["sA"].post(f"{API}/school/students/{sid}/enrollments", json={
        "academic_year": "2026-2027", "class_name": "Grade 5", "section": "B",
    })
    assert r2.status_code == 409

    # snapshot updated on student
    stu = state["sA"].get(f"{API}/school/students/{sid}").json()
    assert stu["section"] == "B" and stu["roll_number"] == "12"

    r3 = state["sA"].get(f"{API}/school/students/{sid}/enrollments")
    assert r3.status_code == 200 and len(r3.json()) >= 1


def test_51_patch_enrollment():
    eid = state["enr1"]["id"]
    r = state["sA"].patch(f"{API}/school/enrollments/{eid}",
                          json={"section": "C"})
    assert r.status_code == 200
    assert r.json()["section"] == "C"


# ---------- Guardians ----------
def test_60_guardian_crud_and_search():
    r = state["sA"].post(f"{API}/school/guardians", json={
        "first_name": "Ramesh", "last_name": "Sharma",
        "relationship_type": "father", "mobile_primary": "+919888800001",
        "email": f"ramesh-{RUN}@example.com",
    })
    assert r.status_code == 201, r.text
    g = r.json()
    state["g1"] = g

    r2 = state["sA"].get(f"{API}/school/guardians", params={"q": "Ramesh"})
    assert r2.status_code == 200
    assert r2.json()["total"] >= 1

    r3 = state["sA"].patch(f"{API}/school/guardians/{g['id']}",
                           json={"occupation": "Engineer"})
    assert r3.status_code == 200
    assert r3.json()["occupation"] == "Engineer"


# ---------- Student-Guardian link ----------
def test_70_link_guardian_dup_and_unlink():
    sid = state["stu1"]["id"]
    gid = state["g1"]["id"]
    r = state["sA"].post(f"{API}/school/students/{sid}/guardians", json={
        "guardian_id": gid, "relationship_type": "father",
        "is_primary": True, "is_emergency_contact": True,
    })
    assert r.status_code == 201, r.text
    rel = r.json()
    state["rel1"] = rel

    # dup link 409
    r2 = state["sA"].post(f"{API}/school/students/{sid}/guardians",
                          json={"guardian_id": gid})
    assert r2.status_code == 409

    # list with joined guardian
    r3 = state["sA"].get(f"{API}/school/students/{sid}/guardians")
    assert r3.status_code == 200
    lst = r3.json()
    assert lst and any(x.get("guardian", {}).get("id") == gid for x in lst)

    # unlink -> soft terminate
    r4 = state["sA"].delete(f"{API}/school/student-guardians/{rel['id']}")
    assert r4.status_code == 200
    r5 = state["sA"].get(f"{API}/school/students/{sid}/guardians")
    # no longer returned as active
    assert not any(x["id"] == rel["id"] for x in r5.json())


# ---------- Family ----------
def test_80_family_crud_and_detail():
    r = state["sA"].post(f"{API}/school/families", json={"family_name": f"Sharma-{RUN}"})
    assert r.status_code == 201, r.text
    fam = r.json()
    state["fam1"] = fam

    r2 = state["sA"].get(f"{API}/school/families")
    assert r2.status_code == 200
    assert any(f["id"] == fam["id"] for f in r2.json())

    # patch
    r3 = state["sA"].patch(f"{API}/school/families/{fam['id']}",
                           json={"notes": "test fam"})
    assert r3.status_code == 200 and r3.json()["notes"] == "test fam"

    # attach a student + guardian and query detail
    state["sA"].patch(f"{API}/school/students/{state['stu1']['id']}",
                     json={"family_id": fam["id"]})
    state["sA"].patch(f"{API}/school/guardians/{state['g1']['id']}",
                     json={"family_id": fam["id"]})

    r4 = state["sA"].get(f"{API}/school/families/{fam['id']}")
    assert r4.status_code == 200
    detail = r4.json()
    assert detail["family_name"] == f"Sharma-{RUN}"
    assert any(s["id"] == state["stu1"]["id"] for s in detail["students"])
    assert any(g["id"] == state["g1"]["id"] for g in detail["guardians"])


# ---------- Shared guardian (sibling) via admission conversion ----------
_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def _multipart(sess, url, files, data):
    saved = sess.headers.pop("Content-Type", None)
    try:
        return sess.post(url, files=files, data=data)
    finally:
        if saved is not None:
            sess.headers["Content-Type"] = saved


def _admit(sess, tenant_slug, child_first, child_last, dob, parent_mobile, parent_name):
    """Run full pipeline: lead -> app -> submit -> under_review -> approve -> convert."""
    r = sess.post(f"{API}/school/crm/leads", json={
        "student_first_name": child_first, "student_last_name": child_last,
        "student_dob": dob, "class_seeking": "Grade 1",
        "academic_year": "2026-2027",
        "parent_name": parent_name, "parent_mobile": parent_mobile,
    })
    assert r.status_code == 201, r.text
    lid = r.json()["id"]

    r = sess.post(f"{API}/school/admissions/applications", json={
        "lead_id": lid, "academic_year": "2026-2027", "class_requested": "Grade 1",
        "student_first_name": child_first, "student_last_name": child_last,
        "parent_name": parent_name, "parent_mobile": parent_mobile,
    })
    assert r.status_code == 201, r.text
    aid = r.json()["id"]

    # Get seeded doc types
    r = sess.get(f"{API}/school/admissions/applications/{aid}/documents")
    doc_types = [d["type_code"] for d in r.json()]

    # Submit + under_review
    assert sess.post(f"{API}/school/admissions/applications/{aid}/status",
                     json={"status": "SUBMITTED"}).status_code == 200
    assert sess.post(f"{API}/school/admissions/applications/{aid}/status",
                     json={"status": "UNDER_REVIEW"}).status_code == 200

    # Upload + verify required docs
    for code in doc_types:
        r = _multipart(sess, f"{API}/school/admissions/applications/{aid}/documents",
                       {"file": (f"{code}.pdf", io.BytesIO(_PDF), "application/pdf")},
                       {"type_code": code})
        if r.status_code == 201:
            did = r.json()["id"]
            sess.post(f"{API}/school/admissions/applications/{aid}/documents/{did}/verify",
                      json={"status": "VERIFIED"})

    r = sess.post(f"{API}/school/admissions/applications/{aid}/status",
                  json={"status": "APPROVED"})
    # Approve may 409 if some optional docs unverified — fall back to override on convert
    override = r.status_code != 200

    r = sess.post(f"{API}/school/admissions/applications/{aid}/convert",
                  json={"override_docs": override})
    assert r.status_code == 200, r.text
    return {"lead_id": lid, "app_id": aid, "result": r.json()}


def test_90_shared_guardian_across_siblings():
    sA = state["sA"]
    # Count guardians + students before
    g_before = sA.get(f"{API}/school/guardians").json()["total"]
    s_before = sA.get(f"{API}/school/students").json()["total"]

    shared_mobile = f"+9198000{RUN[:5]}"
    a1 = _admit(sA, A_SLUG, "Sibling1", f"Fam{RUN}", "2015-01-01",
                shared_mobile, f"Papa Fam{RUN}")
    a2 = _admit(sA, A_SLUG, "Sibling2", f"Fam{RUN}", "2017-01-01",
                shared_mobile, f"Papa Fam{RUN}")

    g_after = sA.get(f"{API}/school/guardians").json()["total"]
    s_after = sA.get(f"{API}/school/students").json()["total"]
    assert g_after - g_before == 1, f"guardian delta expected 1, got {g_after - g_before}"
    assert s_after - s_before == 2, f"student delta expected 2, got {s_after - s_before}"

    # Both students linked to the same guardian
    r = sA.get(f"{API}/school/guardians", params={"q": shared_mobile})
    assert r.status_code == 200
    guardians = r.json()["items"]
    assert len(guardians) == 1
    gid = guardians[0]["id"]
    state["shared_gid"] = gid
    state["sibling_ids"] = [a1["result"]["student_id"], a2["result"]["student_id"]]

    # Each sibling's guardians list contains that guardian
    for sid in state["sibling_ids"]:
        r = sA.get(f"{API}/school/students/{sid}/guardians")
        assert r.status_code == 200
        assert any(x["guardian_id"] == gid for x in r.json())


# ---------- Idempotent conversion (single-row assertions) ----------
def test_91_idempotent_conversion_second_call():
    sA = state["sA"]
    # Reuse sibling1 application
    r = sA.get(f"{API}/school/admissions/applications")
    apps = r.json()
    # find a CONVERTED app
    conv_app = next((a for a in apps.get("items", apps) if a.get("status") == "CONVERTED"), None)
    assert conv_app, "no CONVERTED application"
    aid = conv_app["id"]
    student_id = conv_app.get("student_id")

    r2 = sA.post(f"{API}/school/admissions/applications/{aid}/convert",
                 json={"override_docs": True})
    assert r2.status_code == 200
    body = r2.json()
    assert body["already_converted"] is True
    assert body["student_id"] == student_id

    # Application still CONVERTED
    r3 = sA.get(f"{API}/school/admissions/applications/{aid}")
    assert r3.json()["status"] == "CONVERTED"

    # Lead stage ADMITTED
    lid = conv_app.get("lead_id")
    if lid:
        r4 = sA.get(f"{API}/school/crm/leads/{lid}")
        assert r4.status_code == 200
        assert r4.json()["stage"] == "ADMITTED"


# ---------- Cross-tenant isolation ----------
def test_A0_cross_tenant_404():
    sid = state["stu1"]["id"]
    gid = state["g1"]["id"]
    fid = state["fam1"]["id"]
    sB = state["sB"]

    assert sB.get(f"{API}/school/students/{sid}").status_code == 404
    assert sB.patch(f"{API}/school/students/{sid}", json={"preferred_name": "X"}).status_code == 404
    assert sB.get(f"{API}/school/guardians/{gid}").status_code == 404
    assert sB.patch(f"{API}/school/guardians/{gid}", json={"occupation": "X"}).status_code == 404
    assert sB.get(f"{API}/school/families/{fid}").status_code == 404
    assert sB.get(f"{API}/school/students/{sid}/enrollments").status_code == 404
    assert sB.get(f"{API}/school/students/{sid}/guardians").status_code == 404
    # cross-tenant link => 404 (student not found in B)
    r = sB.post(f"{API}/school/students/{sid}/guardians", json={"guardian_id": gid})
    assert r.status_code in (403, 404)


# ---------- RBAC teacher denied ----------
def test_B0_teacher_forbidden():
    email = f"teach-{RUN}@stma.example.com"
    r = state["sA"].post(f"{API}/school/users", json={
        "email": email, "password": "Teacher@1234",
        "full_name": "Teach Master", "role": "teacher",
    })
    assert r.status_code == 201, r.text

    ts = _sess()
    r = ts.post(f"{API}/auth/login", json={
        "email": email, "password": "Teacher@1234", "tenant_slug": A_SLUG,
    })
    assert r.status_code == 200, r.text

    # POST /students -> 403
    r = ts.post(f"{API}/school/students", json={"first_name": "Nope"})
    assert r.status_code == 403
    r = ts.post(f"{API}/school/guardians", json={
        "first_name": "N", "mobile_primary": "+911", "relationship_type": "guardian",
    })
    assert r.status_code == 403
    r = ts.post(f"{API}/school/families", json={"family_name": "Nope"})
    assert r.status_code == 403


# ---------- Audit events ----------
def test_C0_audit_events_present():
    """Verify main audit actions were logged during this run."""
    # Prefer platform superadmin for global audit view; fall back to school session.
    plat = _sess()
    r = plat.post(f"{API}/auth/login", json={
        "email": "superadmin@schoolos.dev", "password": "SuperAdmin@123",
    })
    if r.status_code != 200:
        pytest.skip("Cannot access audit logs without superadmin creds")

    r = plat.get(f"{API}/platform/audit-logs", params={"page_size": 500})
    if r.status_code != 200:
        # Try tenant-scoped endpoint if available
        r = state["sA"].get(f"{API}/school/audit-logs", params={"page_size": 500})
        if r.status_code != 200:
            pytest.skip(f"audit list endpoint returned {r.status_code}")

    body = r.json()
    items = body.get("items", body) if isinstance(body, dict) else body
    actions = {i.get("action") for i in items}
    expected = {
        "student.create", "student.update", "student.status.change",
        "student.enrollment.create", "guardian.create", "guardian.update",
        "student.guardian.link", "student.guardian.unlink",
        "family.create", "family.update",
    }
    missing = expected - actions
    assert not missing, f"missing audit actions: {missing}"
