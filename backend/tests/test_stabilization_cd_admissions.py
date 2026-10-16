"""Stabilization Workstreams C + D — end-to-end admissions + applicant-facing form."""
import os
import uuid

import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://schoolos-foundation-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"
RUN = uuid.uuid4().hex[:6]
SLUG = f"stc-{RUN}"
EMAIL = f"owner-{RUN}@stc.example.com"
PW = "SchoolOwner@123"
st: dict = {}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def _code(r):
    b = r.json()
    d = b.get("error", {}).get("details") or b.get("detail")
    return d.get("code") if isinstance(d, dict) else None


def _lead(s, lid):
    return s.get(f"{API}/school/crm/leads/{lid}").json()


def test_00_bootstrap():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/register-school", json={
        "school_name": f"STC {RUN}", "slug": SLUG, "contact_email": EMAIL,
        "owner_full_name": "Owner", "owner_email": EMAIL, "owner_password": PW})
    assert r.status_code == 201, r.text
    st["s"] = s
    lead = s.post(f"{API}/school/crm/leads", json={
        "student_first_name": "Asha", "student_last_name": "Rao", "parent_name": "Ravi Rao",
        "parent_mobile": f"98{RUN[:4].encode().hex()[:8]}", "class_seeking": "Grade 1", "academic_year": "2026-27"})
    assert lead.status_code == 201, lead.text
    st["lead"] = lead.json()
    assert st["lead"]["stage"] == "NEW_INQUIRY"


def test_10_contact_activity_advances_to_contacted():
    s = st["s"]; lid = st["lead"]["id"]
    r = s.post(f"{API}/school/crm/leads/{lid}/activities", json={
        "activity_type": "phone_call", "subject": "Intro call", "next_followup_at": "2020-01-01T10:00:00+00:00"})
    assert r.status_code == 201, r.text
    assert _lead(s, lid)["stage"] == "CONTACTED"
    q = s.get(f"{API}/school/crm/followups", params={"bucket": "overdue"}).json()
    fu = next(f for f in q if f["lead_id"] == lid)
    assert fu["lead_name"] == "Asha Rao" and fu["inquiry_number"]
    st["fu"] = fu


def test_11_complete_followup_logs_activity():
    s = st["s"]; lid = st["lead"]["id"]
    r = s.patch(f"{API}/school/crm/followups/{st['fu']['id']}", json={"status": "completed", "completion_notes": "Parent keen"})
    assert r.status_code == 200
    acts = s.get(f"{API}/school/crm/leads/{lid}/activities").json()
    assert any("Follow-up done" in (a.get("subject") or "") for a in acts)
    assert _lead(s, lid)["next_followup_at"] is None


def test_12_visit_advances_and_completion_logged():
    s = st["s"]; lid = st["lead"]["id"]
    v = s.post(f"{API}/school/crm/visits", json={"lead_id": lid, "scheduled_date": "2026-11-02",
                                                 "start_time": "10:00", "end_time": "10:30"})
    assert v.status_code == 201, v.text
    assert _lead(s, lid)["stage"] == "VISIT_SCHEDULED"
    lst = s.get(f"{API}/school/crm/visits").json()
    assert next(x for x in lst if x["id"] == v.json()["id"])["lead_name"] == "Asha Rao"
    u = s.patch(f"{API}/school/crm/visits/{v.json()['id']}", json={"status": "completed"})
    assert u.status_code == 200
    acts = s.get(f"{API}/school/crm/leads/{lid}/activities").json()
    assert any(a.get("subject") == "Campus visit completed" for a in acts)


def test_13_manual_application_stages_blocked():
    s = st["s"]; lid = st["lead"]["id"]
    for stage in ("APPROVED", "FEE_PENDING", "ADMITTED", "FORM_FILLED"):
        r = s.post(f"{API}/school/crm/leads/{lid}/stage", json={"stage": stage})
        assert r.status_code == 409 and _code(r) == "stage_managed_by_application", stage
    r = s.post(f"{API}/school/crm/leads/{lid}/stage", json={"stage": "LOST"})
    assert r.status_code == 400


def test_20_staff_sends_applicant_link():
    s = st["s"]; lid = st["lead"]["id"]
    r = s.post(f"{API}/school/admissions/applicant-links", json={"lead_id": lid})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["url_path"].startswith("/apply/t/") and len(body["token"]) > 30
    st["token"] = body["token"]; st["app_id"] = body["application_id"]
    assert _lead(s, lid)["stage"] == "FORM_FILLED"
    # Re-issue revokes previous token
    r2 = s.post(f"{API}/school/admissions/applicant-links", json={"lead_id": lid})
    assert r2.status_code == 201 and r2.json()["application_id"] == st["app_id"]
    old = requests.get(f"{API}/public/admissions/t/{st['token']}")
    assert old.status_code == 404 and _code(old) == "link_invalid"
    st["token"] = r2.json()["token"]
    links = s.get(f"{API}/school/admissions/applications/{st['app_id']}/applicant-links").json()
    assert [l["status"] for l in links][:2] == ["active", "revoked"] and "token" not in links[0]


def test_21_applicant_views_edits_uploads_submits():
    t = st["token"]
    v = requests.get(f"{API}/public/admissions/t/{t}")
    assert v.status_code == 200, v.text
    view = v.json()
    assert view["status"] == "DRAFT" and view["editable"] and view["application"]["student_first_name"] == "Asha"
    assert "storage_key" not in str(view)
    form = {**{k: view["application"][k] for k in ("student_first_name", "student_last_name", "parent_name", "parent_mobile")},
            "academic_year": "2026-27", "class_requested": "Grade 1", "student_dob": "2020-05-05", "address": "12 MG Road"}
    u = requests.put(f"{API}/public/admissions/t/{t}", json=form)
    assert u.status_code == 200, u.text
    bad = requests.put(f"{API}/public/admissions/t/{t}", json={**form, "student_dob": ""})
    assert bad.status_code == 422 and _code(bad) == "invalid_application"
    up = requests.post(f"{API}/public/admissions/t/{t}/documents", data={"type_code": "birth_certificate"},
                       files={"file": ("bc.png", PNG, "image/png")})
    assert up.status_code == 201, up.text
    doc = next(d for d in up.json()["documents"] if d["type_code"] == "birth_certificate")
    assert doc["filename"] == "bc.png" and doc["status"] == "PENDING"
    exe = requests.post(f"{API}/public/admissions/t/{t}/documents", data={"type_code": "birth_certificate"},
                        files={"file": ("x.exe", b"MZ", "application/x-msdownload")})
    assert exe.status_code == 415
    sub = requests.post(f"{API}/public/admissions/t/{t}/submit")
    assert sub.status_code == 200 and sub.json()["status"] == "SUBMITTED" and not sub.json()["editable"]
    again = requests.put(f"{API}/public/admissions/t/{t}", json=form)
    assert again.status_code == 409


def test_22_staff_sees_upload_and_reviews():
    s = st["s"]; aid = st["app_id"]
    app = s.get(f"{API}/school/admissions/applications/{aid}").json()
    assert app["status"] == "SUBMITTED" and app["address"] == "12 MG Road"
    docs = s.get(f"{API}/school/admissions/applications/{aid}/documents").json()
    bc = next(d for d in docs if d["type_code"] == "birth_certificate")
    dl = s.get(f"{API}/school/admissions/applications/{aid}/documents/{bc['id']}/download")
    assert dl.status_code == 200 and dl.content == PNG
    # Staff uploads + verifies the remaining required docs
    s.headers.pop("Content-Type", None)
    for d in docs:
        if d["type_code"] != "birth_certificate":
            s.post(f"{API}/school/admissions/applications/{aid}/documents", data={"type_code": d["type_code"]},
                   files={"file": (f"{d['type_code']}.png", PNG, "image/png")})
    s.headers["Content-Type"] = "application/json"
    for d in s.get(f"{API}/school/admissions/applications/{aid}/documents").json():
        r = s.post(f"{API}/school/admissions/applications/{aid}/documents/{d['id']}/verify", json={"status": "VERIFIED"})
        assert r.status_code == 200, r.text
    assert s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "UNDER_REVIEW"}).status_code == 200
    assert _lead(s, st["lead"]["id"])["stage"] == "UNDER_REVIEW"
    # Verified doc cannot be replaced by applicant
    r = requests.post(f"{API}/public/admissions/t/{st['token']}/documents", data={"type_code": "birth_certificate"},
                      files={"file": ("bc2.png", PNG, "image/png")})
    assert r.status_code == 409 and _code(r) == "already_verified"


def test_30_approve_sets_fee_pending_and_blocks_conversion():
    s = st["s"]; aid = st["app_id"]
    r = s.post(f"{API}/school/admissions/applications/{aid}/status", json={"status": "APPROVED"})
    assert r.status_code == 200, r.text
    assert r.json()["fee_status"] == "pending"
    assert _lead(s, st["lead"]["id"])["stage"] == "FEE_PENDING"
    c = s.post(f"{API}/school/admissions/applications/{aid}/convert", json={"override_docs": False})
    assert c.status_code == 409 and _code(c) == "fee_pending"
    nr = s.post(f"{API}/school/admissions/applications/{aid}/fee-status", json={"status": "received"})
    assert nr.status_code == 400
    # Applicant link closes once approved
    assert requests.get(f"{API}/public/admissions/t/{st['token']}").status_code == 410


def test_31_fee_received_then_idempotent_conversion():
    s = st["s"]; aid = st["app_id"]
    f = s.post(f"{API}/school/admissions/applications/{aid}/fee-status", json={"status": "received", "reference": "RCPT-001"})
    assert f.status_code == 200 and f.json()["fee_status"] == "received" and f.json()["fee_reference"] == "RCPT-001"
    c1 = s.post(f"{API}/school/admissions/applications/{aid}/convert", json={"override_docs": False})
    assert c1.status_code == 200, c1.text
    c2 = s.post(f"{API}/school/admissions/applications/{aid}/convert", json={"override_docs": False})
    assert c2.json()["already_converted"] is True and c2.json()["student_id"] == c1.json()["student_id"]
    lead = _lead(s, st["lead"]["id"])
    assert lead["stage"] == "ADMITTED" and lead["student_id"] == c1.json()["student_id"]
    stu = s.get(f"{API}/school/students/{c1.json()['student_id']}")
    assert stu.status_code == 200


def test_40_form_config_and_public_apply():
    s = st["s"]
    r = s.put(f"{API}/school/admissions/form-config", json={
        "enabled": True, "intro_text": "Welcome", "academic_years": ["2026-27"], "classes": ["Grade 1", "Grade 2"],
        "fields": {"student_dob": {"enabled": True, "required": True}, "address": {"enabled": False}},
        "custom_questions": [{"label": "How did you hear about us?", "type": "select", "options": ["Friend", "Ad"], "required": True}]})
    assert r.status_code == 200, r.text
    assert r.json()["public_path"] == f"/apply/{SLUG}"
    f = requests.get(f"{API}/public/admissions/schools/{SLUG}/form")
    assert f.status_code == 200
    form = f.json()
    assert form["options"]["classes"] == ["Grade 1", "Grade 2"] and form["custom_questions"][0]["key"].startswith("q_")
    qk = form["custom_questions"][0]["key"]
    assert form["document_types"]
    base = {"academic_year": "2026-27", "class_requested": "Grade 2", "student_first_name": "Neel", "student_last_name": "Das",
            "student_dob": "2019-01-01", "parent_name": "Mira Das", "parent_mobile": "+91 98765 43210"}
    bad = requests.post(f"{API}/public/admissions/schools/{SLUG}/apply", json={**base, "class_requested": "Grade 9"})
    assert bad.status_code == 422
    missing_q = requests.post(f"{API}/public/admissions/schools/{SLUG}/apply", json=base)
    assert missing_q.status_code == 422
    bot = requests.post(f"{API}/public/admissions/schools/{SLUG}/apply", json={**base, "form_answers": {qk: "Ad"}, "website": "spam"})
    assert bot.status_code == 400
    ok = requests.post(f"{API}/public/admissions/schools/{SLUG}/apply", json={**base, "form_answers": {qk: "Friend"}, "address": "ignored"})
    assert ok.status_code == 201, ok.text
    body = ok.json()
    view = requests.get(f"{API}/public/admissions/t/{body['token']}").json()
    assert view["status"] == "SUBMITTED" and view["can_upload"] and view["application"]["form_answers"] == {qk: "Friend"}
    assert view["application"]["address"] is None
    apps = s.get(f"{API}/school/admissions/applications", params={"q": "Neel"}).json()["items"]
    assert apps and apps[0]["submitted_via"] == "public_form"
    lead = _lead(s, apps[0]["lead_id"])
    assert lead["source"] == "website" and lead["stage"] == "FORM_FILLED"


def test_41_disabled_form_and_unknown_school():
    s = st["s"]
    s.put(f"{API}/school/admissions/form-config", json={"enabled": False})
    r = requests.get(f"{API}/public/admissions/schools/{SLUG}/form")
    assert r.status_code == 404 and _code(r) == "form_disabled"
    assert requests.get(f"{API}/public/admissions/schools/no-such-{RUN}/form").status_code == 404
    assert requests.get(f"{API}/public/admissions/t/not-a-real-token").status_code == 404
    s.put(f"{API}/school/admissions/form-config", json={"enabled": True})
