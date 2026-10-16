"""Iteration 19 retest of C+D fixes: /status CONVERTED blocked, XFF rate-limit, stage guard,
stable custom question keys, human validation labels, note activity for auto stage w/o application."""
import os
import uuid

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE}/api/v1"
RUN = uuid.uuid4().hex[:6]
SLUG = f"test-stab-{RUN}"
EMAIL = f"owner-{RUN}@test-stab.example.com"
PW = "SchoolOwner@123"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def _code(r):
    try:
        b = r.json()
    except Exception:
        return None
    d = (b.get("error") or {}).get("details") or b.get("detail")
    return d.get("code") if isinstance(d, dict) else None


@pytest.fixture(scope="module")
def s():
    sess = requests.Session(); sess.headers.update({"Content-Type": "application/json"})
    r = sess.post(f"{API}/auth/register-school", json={
        "school_name": f"Stab {RUN}", "slug": SLUG, "contact_email": EMAIL,
        "owner_full_name": "Owner", "owner_email": EMAIL, "owner_password": PW})
    assert r.status_code == 201, r.text
    return sess


def _lead(s, name="Kiran"):
    r = s.post(f"{API}/school/crm/leads", json={
        "student_first_name": name, "student_last_name": "Test", "parent_name": "Parent Test",
        "parent_mobile": f"9{uuid.uuid4().int % 10**9:09d}", "class_seeking": "Grade 1", "academic_year": "2026-27"})
    assert r.status_code == 201, r.text
    return r.json()


def _app(s, lid):
    r = s.post(f"{API}/school/admissions/applicant-links", json={"lead_id": lid})
    assert r.status_code == 201, r.text
    return r.json()


def _verify_all(s, aid):
    s.headers.pop("Content-Type", None)
    for d in s.get(f"{API}/school/admissions/applications/{aid}/documents").json():
        s.post(f"{API}/school/admissions/applications/{aid}/documents", data={"type_code": d["type_code"]},
               files={"file": (f"{d['type_code']}.png", PNG, "image/png")})
    s.headers["Content-Type"] = "application/json"
    for d in s.get(f"{API}/school/admissions/applications/{aid}/documents").json():
        s.post(f"{API}/school/admissions/applications/{aid}/documents/{d['id']}/verify", json={"status": "VERIFIED"})


# Fix 1: /status CONVERTED -> 409 use_convert_endpoint
def test_status_converted_blocked(s):
    lead = _lead(s, "Bypass"); aid = _app(s, lead["id"])["application_id"]
    _verify_all(s, aid)
    for stt in ("SUBMITTED", "UNDER_REVIEW", "APPROVED"):
        assert s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": stt}).status_code == 200
    r = s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "CONVERTED"})
    assert r.status_code == 409 and _code(r) == "use_convert_endpoint", r.text
    ld = s.get(f"{API}/school/crm/leads/{lead['id']}").json()
    assert ld["stage"] == "FEE_PENDING" and not ld.get("student_id")
    # even after fee received, /status CONVERTED still blocked; /convert works
    s.post(f"{API}/school/admissions/applications/{aid}/fee-status", json={"status": "received", "reference": "R1"})
    assert s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "CONVERTED"}).status_code == 409
    c = s.post(f"{API}/school/admissions/applications/{aid}/convert", json={"override_docs": False})
    assert c.status_code == 200, c.text
    assert s.get(f"{API}/school/crm/leads/{lead['id']}").json()["stage"] == "ADMITTED"


# Fix 3: stage guard
def test_stage_guard(s):
    lead = _lead(s, "Guard"); aid = _app(s, lead["id"])["application_id"]
    s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "SUBMITTED"})
    for stage in ("NEW_INQUIRY", "CONTACTED", "VISIT_SCHEDULED"):
        r = s.post(f"{API}/school/crm/leads/{lead['id']}/stage", json={"stage": stage})
        assert r.status_code == 409 and _code(r) == "stage_managed_by_application", (stage, r.text)
    r = s.post(f"{API}/school/crm/leads/{lead['id']}/stage", json={"stage": "LOST", "reason": "Family relocated"})
    assert r.status_code == 409 and _code(r) == "stage_managed_by_application", r.text


# Fix: stable custom question keys + human validation labels
def test_question_keys_stable_and_labels(s):
    r = s.put(f"{API}/school/admissions/form-config", json={
        "enabled": True, "academic_years": ["2026-27"], "classes": ["Grade 1", "Grade 2"],
        "fields": {"student_dob": {"enabled": True, "required": True}},
        "custom_questions": [{"label": "Sibling in school?", "type": "select", "options": ["Yes", "No"], "required": True}]})
    k1 = r.json()["custom_questions"][0]["key"]
    assert k1.startswith("q_") and len(k1) == 8
    cfg = r.json()
    cfg["custom_questions"][0]["label"] = "Sibling studying here?"
    cfg["custom_questions"].insert(0, {"label": "Transport needed?", "type": "text"})
    r2 = s.put(f"{API}/school/admissions/form-config", json={k: cfg[k] for k in ("enabled", "academic_years", "classes", "fields", "custom_questions")})
    qs = r2.json()["custom_questions"]
    assert qs[1]["key"] == k1 and qs[1]["label"] == "Sibling studying here?" and qs[0]["key"] != k1
    base = {"academic_year": "2026-27", "class_requested": "Grade 2", "student_first_name": "Vik", "student_last_name": "Lal",
            "parent_name": "Pat Parent", "parent_mobile": "+91 98765 43210"}
    bad = requests.post(f"{API}/public/admissions/schools/{SLUG}/apply", json=base, headers={"X-Forwarded-For": "10.251.0.1"})
    assert bad.status_code == 422
    msg = str(bad.json())
    assert "Date of birth: required" in msg and "Sibling studying here?: required" in msg, msg
    assert "student_dob" not in (bad.json().get("detail") or {}).get("message", msg.split("errors")[0])


# Fix: auto stage change without application logged as note
def test_auto_stage_note_activity(s):
    lead = _lead(s, "Noted")
    s.post(f"{API}/school/crm/leads/{lead['id']}/activities", json={"activity_type": "phone_call", "subject": "called"})
    ld = s.get(f"{API}/school/crm/leads/{lead['id']}").json()
    assert ld["stage"] == "CONTACTED"
    acts = s.get(f"{API}/school/crm/leads/{lead['id']}/activities").json()
    acts = acts.get("items", acts) if isinstance(acts, dict) else acts
    types = [a["activity_type"] for a in acts]
    print("activity types:", types)
    assert "application_update" not in types



# Rate limit keyed on the right-most (proxy-appended) XFF hop — client-rotated headers don't bypass it
def test_zz_rate_limit_xff(s):
    s.put(f"{API}/school/admissions/form-config", json={"enabled": True, "academic_years": ["2026-27"], "classes": ["Grade 1"]})
    base = {"academic_year": "2026-27", "class_requested": "Grade 1", "student_first_name": "Rate", "student_last_name": "Lal", "student_dob": "2020-01-01",
            "parent_name": "Pat Parent", "parent_mobile": "+91 98765 43210"}
    codes = [requests.post(f"{API}/public/admissions/schools/{SLUG}/apply", json=base).status_code for _ in range(12)]
    assert 429 in codes, codes
    spoof = requests.post(f"{API}/public/admissions/schools/{SLUG}/apply", json=base, headers={"X-Forwarded-For": "10.250.9.9"})
    assert spoof.status_code == 429, spoof.text
