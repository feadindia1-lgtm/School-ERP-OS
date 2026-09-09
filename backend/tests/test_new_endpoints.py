"""Tests for 3 new endpoints introduced for Prompt 3 UI."""
import os
import time
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"


def _register():
    ts = int(time.time() * 1000000)
    slug = f"t{ts}"
    payload = {
        "school_name": f"School {slug}",
        "slug": slug,
        "contact_email": f"admin+{slug}@example.com",
        "owner_full_name": "Owner",
        "owner_email": f"owner+{slug}@example.com",
        "owner_password": "Owner@1234",
    }
    s = requests.Session()
    r = s.post(f"{BASE}/auth/register-school", json=payload)
    assert r.status_code in (200, 201), r.text
    lr = s.post(f"{BASE}/auth/login", json={"email": payload["owner_email"], "password": payload["owner_password"]})
    assert lr.status_code == 200, lr.text
    return s


def _mk_student(s, first, dob=None, ay="2025-26"):
    body = {"first_name": first, "academic_year": ay}
    if dob:
        body["date_of_birth"] = dob
    r = s.post(f"{BASE}/school/students", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_stats_and_timeline_and_isolation():
    sA = _register()
    sB = _register()

    a1 = _mk_student(sA, "Alice", dob="2010-01-01")
    _mk_student(sA, "Bob")  # missing DOB
    _mk_student(sB, "Foreign", dob="2011-05-05")

    r = sA.get(f"{BASE}/school/students/stats?academic_year=2025-26")
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("total", "active", "new_this_year", "missing_info", "missing_dob", "missing_guardians"):
        assert k in d, f"missing key {k}: {d}"
    assert d["total"] == 2
    assert d["new_this_year"] == 2
    assert d["missing_dob"] >= 1
    assert d["missing_guardians"] >= 2  # neither student has guardians

    rb = sB.get(f"{BASE}/school/students/stats?academic_year=2025-26")
    assert rb.status_code == 200
    assert rb.json()["total"] == 1

    # timeline
    tl = sA.get(f"{BASE}/school/students/{a1['id']}/timeline")
    assert tl.status_code == 200
    assert isinstance(tl.json(), list)

    # foreign tenant blocked
    fx = sB.get(f"{BASE}/school/students/{a1['id']}/timeline")
    assert fx.status_code == 404
    fx2 = sB.get(f"{BASE}/school/students/{a1['id']}")
    assert fx2.status_code == 404


def test_guardian_students_endpoint():
    s = _register()
    kid = _mk_student(s, "Kid")
    g = s.post(f"{BASE}/school/guardians", json={
        "first_name": "Parent", "last_name": "One", "mobile_primary": "9990001111", "relation": "father",
    })
    assert g.status_code == 201, g.text
    gid = g.json()["id"]

    link = s.post(f"{BASE}/school/students/{kid['id']}/guardians", json={
        "guardian_id": gid, "relation": "father", "is_primary": True,
    })
    assert link.status_code == 201, link.text

    r = s.get(f"{BASE}/school/guardians/{gid}/students")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    stud = rows[0].get("student") or {}
    assert stud.get("id") == kid["id"] or rows[0].get("student_id") == kid["id"]

    # cross-tenant
    sB = _register()
    fx = sB.get(f"{BASE}/school/guardians/{gid}/students")
    assert fx.status_code == 404
