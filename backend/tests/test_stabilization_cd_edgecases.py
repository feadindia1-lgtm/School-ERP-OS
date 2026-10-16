"""Stabilization C+D edge cases (iteration_18): manual stage guard, backwards moves, reject/withdraw -> LOST,
fee rule off, status-endpoint conversion bypass, applicant link closure, upload limits, public form validation."""
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
st: dict = {}


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


def _new_lead(s, name="Kiran"):
    r = s.post(f"{API}/school/crm/leads", json={
        "student_first_name": name, "student_last_name": "Test", "parent_name": "Parent Test",
        "parent_mobile": f"9{uuid.uuid4().int % 10**9:09d}", "class_seeking": "Grade 1", "academic_year": "2026-27"})
    assert r.status_code == 201, r.text
    return r.json()


def _lead(s, lid):
    return s.get(f"{API}/school/crm/leads/{lid}").json()


def _app_for(s, lid):
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


def _to_review(s, aid):
    for stt in ("SUBMITTED", "UNDER_REVIEW"):
        r = s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": stt})
        assert r.status_code == 200, r.text


# Manual stage moves
def test_manual_stage_allowed_moves(s):
    lead = _new_lead(s)
    for stage in ("CONTACTED", "VISIT_SCHEDULED", "NEW_INQUIRY"):
        r = s.post(f"{API}/school/crm/leads/{lead['id']}/stage", json={"stage": stage})
        assert r.status_code == 200 and r.json()["stage"] == stage, r.text
    r = s.post(f"{API}/school/crm/leads/{lead['id']}/stage", json={"stage": "LOST", "reason": "Chose another school"})
    assert r.status_code == 200 and r.json()["stage"] == "LOST" and r.json().get("lost_reason") == "Chose another school"


def test_contact_on_later_stage_does_not_go_backwards(s):
    lead = _new_lead(s)
    s.post(f"{API}/school/crm/visits", json={"lead_id": lead["id"], "scheduled_date": "2026-12-01", "start_time": "09:00", "end_time": "09:30"})
    assert _lead(s, lead["id"])["stage"] == "VISIT_SCHEDULED"
    s.post(f"{API}/school/crm/leads/{lead['id']}/activities", json={"activity_type": "whatsapp", "subject": "hi"})
    assert _lead(s, lead["id"])["stage"] == "VISIT_SCHEDULED"
    # note activity on NEW_INQUIRY shouldn't move
    l2 = _new_lead(s, "Noted")
    s.post(f"{API}/school/crm/leads/{l2['id']}/activities", json={"activity_type": "note", "subject": "n"})
    assert _lead(s, l2["id"])["stage"] == "NEW_INQUIRY"


def test_manual_backwards_from_application_stage(s):
    """Report-only: can staff manually drag an UNDER_REVIEW lead back to NEW_INQUIRY?"""
    lead = _new_lead(s, "Backward")
    link = _app_for(s, lead["id"]); _to_review(s, link["application_id"])
    assert _lead(s, lead["id"])["stage"] == "UNDER_REVIEW"
    r = s.post(f"{API}/school/crm/leads/{lead['id']}/stage", json={"stage": "NEW_INQUIRY"})
    st["backwards_status"] = r.status_code
    print("manual backwards UNDER_REVIEW->NEW_INQUIRY:", r.status_code, r.text[:200])


def test_reject_sets_lost_and_closes_link(s):
    lead = _new_lead(s, "Reject")
    link = _app_for(s, lead["id"]); aid = link["application_id"]
    _to_review(s, aid)
    assert s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "REJECTED"}).status_code == 400
    r = s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "REJECTED", "reason": "No seats"})
    assert r.status_code == 200
    ld = _lead(s, lead["id"])
    assert ld["stage"] == "LOST"
    v = requests.get(f"{API}/public/admissions/t/{link['token']}")
    assert v.status_code == 410 and _code(v) == "application_closed"
    # Link on closed app -> 409
    r2 = s.post(f"{API}/school/admissions/applicant-links", json={"lead_id": lead["id"]})
    assert r2.status_code == 409 and _code(r2) == "application_closed"


def test_withdraw_sets_lost(s):
    lead = _new_lead(s, "Withdraw")
    link = _app_for(s, lead["id"])
    r = s.post(f"{API}/school/admissions/applications/{link['application_id']}/status", json={"status": "WITHDRAWN", "reason": "moved"})
    assert r.status_code == 200
    assert _lead(s, lead["id"])["stage"] == "LOST"


def test_status_endpoint_cannot_bypass_conversion(s):
    """APPROVED -> CONVERTED via /status would skip the fee gate & student creation."""
    lead = _new_lead(s, "Bypass")
    link = _app_for(s, lead["id"]); aid = link["application_id"]
    _verify_all(s, aid); _to_review(s, aid)
    assert s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "APPROVED"}).json()["fee_status"] == "pending"
    r = s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "CONVERTED"})
    ld = _lead(s, lead["id"])
    print("status->CONVERTED:", r.status_code, "lead stage", ld["stage"], "student", ld.get("student_id"))
    assert r.status_code in (400, 409), f"fee gate bypass: /status CONVERTED returned {r.status_code}, lead={ld['stage']}"


def test_admitted_lead_cannot_move_and_fee_errors(s):
    lead = _new_lead(s, "Admit")
    link = _app_for(s, lead["id"]); aid = link["application_id"]
    # fee-status before approval -> 409 not_approved
    r = s.post(f"{API}/school/admissions/applications/{aid}/fee-status", json={"status": "received", "reference": "X"})
    assert r.status_code == 409 and _code(r) == "not_approved"
    _verify_all(s, aid); _to_review(s, aid)
    s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "APPROVED"})
    assert s.post(f"{API}/school/admissions/applications/{aid}/fee-status", json={"status": "bogus"}).status_code == 400
    assert s.post(f"{API}/school/admissions/applications/{aid}/fee-status", json={"status": "received", "reference": "  "}).status_code == 400
    assert s.post(f"{API}/school/admissions/applications/{aid}/fee-status", json={"status": "received", "reference": "R1"}).status_code == 200
    c = s.post(f"{API}/school/admissions/applications/{aid}/convert", json={"override_docs": False})
    assert c.status_code == 200, c.text
    r = s.post(f"{API}/school/crm/leads/{lead['id']}/stage", json={"stage": "CONTACTED"})
    assert r.status_code == 409 and _code(r) == "lead_admitted"
    r = s.post(f"{API}/school/crm/leads/{lead['id']}/stage", json={"stage": "LOST", "reason": "x"})
    assert r.status_code == 409


def test_fee_rule_off_approved_stage_and_convert(s):
    r = s.patch(f"{API}/school/crm/settings", json={"require_fee_before_conversion": False})
    assert r.status_code == 200 and r.json()["require_fee_before_conversion"] is False
    try:
        lead = _new_lead(s, "NoFee")
        link = _app_for(s, lead["id"]); aid = link["application_id"]
        _verify_all(s, aid); _to_review(s, aid)
        a = s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "APPROVED"}).json()
        assert a.get("fee_status") in (None, "")
        assert _lead(s, lead["id"])["stage"] == "APPROVED"
        c = s.post(f"{API}/school/admissions/applications/{aid}/convert", json={"override_docs": False})
        assert c.status_code == 200, c.text
        assert _lead(s, lead["id"])["stage"] == "ADMITTED"
    finally:
        s.patch(f"{API}/school/crm/settings", json={"require_fee_before_conversion": True})


def test_upload_limits_and_unknown_type(s):
    lead = _new_lead(s, "Upload")
    t = _app_for(s, lead["id"])["token"]
    big = requests.post(f"{API}/public/admissions/t/{t}/documents", data={"type_code": "birth_certificate"},
                        files={"file": ("big.pdf", b"0" * (10 * 1024 * 1024 + 10), "application/pdf")})
    assert big.status_code == 413, big.status_code
    unk = requests.post(f"{API}/public/admissions/t/{t}/documents", data={"type_code": "nope"},
                        files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")})
    assert unk.status_code == 400
    ok = requests.post(f"{API}/public/admissions/t/{t}/documents", data={"type_code": "birth_certificate"},
                       files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")})
    assert ok.status_code == 201


def test_public_form_required_field_and_submit_validation(s):
    s.put(f"{API}/school/admissions/form-config", json={"enabled": True, "fields": {"parent_email": {"enabled": True, "required": True}}})
    base = {"academic_year": "2026-27", "class_requested": "Grade 1", "student_first_name": "P", "student_last_name": "Q",
            "parent_name": "PQ Parent", "parent_mobile": "+91 90000 11111", "student_dob": "2020-01-01"}
    r = requests.post(f"{API}/public/admissions/schools/{SLUG}/apply", json=base)
    assert r.status_code == 422 and _code(r) == "invalid_application"
    r = requests.post(f"{API}/public/admissions/schools/{SLUG}/apply", json={**base, "parent_email": "bad"})
    assert r.status_code == 422
    r = requests.post(f"{API}/public/admissions/schools/{SLUG.upper()}/apply", json={**base, "parent_email": "a@b.co"})
    assert r.status_code == 201, r.text
    view = requests.get(f"{API}/public/admissions/t/{r.json()['token']}").json()
    assert view["status"] == "SUBMITTED" and view["editable"] is False
    sub = requests.post(f"{API}/public/admissions/t/{r.json()['token']}/submit")
    assert sub.status_code == 409 and _code(sub) == "already_submitted"
    s.put(f"{API}/school/admissions/form-config", json={"enabled": True})


def test_staff_endpoints_require_auth():
    for m, p in (("get", "/school/admissions/form-config"), ("post", "/school/admissions/applicant-links"),
                 ("put", "/school/admissions/form-config")):
        r = getattr(requests, m)(f"{API}{p}", json={})
        assert r.status_code == 401, (p, r.status_code)


def test_form_config_validation(s):
    r = s.put(f"{API}/school/admissions/form-config", json={"link_expiry_days": 0})
    assert r.status_code == 422
    r = s.put(f"{API}/school/admissions/form-config", json={"enabled": True, "custom_questions": [
        {"label": "", "type": "text"}, {"label": "Q", "type": "evil"}]})
    assert r.status_code == 200
    qs = r.json()["custom_questions"]
    assert len(qs) == 1 and qs[0]["type"] == "text"
    print("custom question key after blank skipped:", qs[0]["key"])
    s.put(f"{API}/school/admissions/form-config", json={"enabled": True})
