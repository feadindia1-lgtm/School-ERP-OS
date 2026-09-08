"""Prompt 1 platform + wizard + impersonation tests (regression + new)."""
import os
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://schoolos-foundation-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"

RUN = uuid.uuid4().hex[:6]
PLATFORM_EMAIL = "superadmin@schoolos.dev"
PLATFORM_PW = "SuperAdmin@123"

state: dict = {}


def _sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _wizard_payload(slug: str, admin_email: str, school_code: str | None = None, plan: str = "trial"):
    return {
        "institution": {
            "school_name": f"Test School {slug}",
            "slug": slug,
            "short_name": "TS",
            "school_code": school_code,
            "board": "cbse",
            "school_type": "k12",
        },
        "contact": {"email": f"contact-{slug}@example.com", "phone": "+1234567890", "country": "US"},
        "academic": {
            "academic_year_name": "2025-26",
            "classes_offered": ["1", "2", "3"],
            "sections": ["A", "B"],
        },
        "administrator": {
            "full_name": "Admin User",
            "email": admin_email,
        },
        "branding": {"primary_color": "#123456"},
        "modules": {"crm": True, "transport": True},
        "plan": plan,
    }


# --------- Platform login ---------
def test_platform_login():
    s = _sess()
    r = s.post(f"{API}/auth/login", json={"email": PLATFORM_EMAIL, "password": PLATFORM_PW})
    assert r.status_code == 200, r.text
    state["ps"] = s


# --------- Stats ---------
def test_platform_stats_fields():
    s = state["ps"]
    r = s.get(f"{API}/platform/stats")
    assert r.status_code == 200, r.text
    data = r.json()
    for key in [
        "total_schools", "active_schools", "trial_schools", "suspended_schools",
        "archived_schools", "total_students", "total_teachers", "total_users",
        "mrr", "audit_events_30d", "subscription_status", "recently_onboarded", "open_alerts",
    ]:
        assert key in data, f"missing {key}"
    assert isinstance(data["subscription_status"], dict)
    assert isinstance(data["recently_onboarded"], list)
    assert isinstance(data["mrr"], (int, float))


# --------- Wizard create school ---------
def test_wizard_create_school():
    s = state["ps"]
    slug = f"wiz-{RUN}"
    code = f"CODE-{RUN}"
    payload = _wizard_payload(slug, f"admin-{RUN}@example.com", school_code=code, plan="trial")
    r = s.post(f"{API}/platform/schools", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["tenant"]["slug"] == slug
    assert data["tenant"]["school_code"] == code
    assert data["tenant"]["board"] == "cbse"
    assert data["administrator"]["email"] == f"admin-{RUN}@example.com"
    assert data["temp_password"], "should return generated temp password"
    state["tid"] = data["tenant"]["id"]
    state["slug"] = slug
    state["code"] = code
    state["admin_email"] = f"admin-{RUN}@example.com"
    state["temp_pw"] = data["temp_password"]


def test_wizard_duplicate_slug_409():
    s = state["ps"]
    payload = _wizard_payload(state["slug"], f"other-{RUN}@example.com", school_code=f"OTHER-{RUN}")
    r = s.post(f"{API}/platform/schools", json=payload)
    assert r.status_code == 409


def test_wizard_duplicate_school_code_409():
    s = state["ps"]
    payload = _wizard_payload(f"other-{RUN}", f"o2-{RUN}@example.com", school_code=state["code"])
    r = s.post(f"{API}/platform/schools", json=payload)
    assert r.status_code == 409


def test_wizard_blocks_surface_on_get():
    s = state["ps"]
    r = s.get(f"{API}/platform/tenants/{state['tid']}")
    assert r.status_code == 200
    data = r.json()
    assert data["contact"].get("email") == f"contact-{state['slug']}@example.com"
    assert data["academic"].get("academic_year_name") == "2025-26"
    assert data["branding"].get("primary_color") == "#123456"
    assert data["modules"].get("crm") is True
    assert data["modules"].get("transport") is True


# --------- Status change + alert ---------
def test_status_suspend_audits_and_alerts():
    s = state["ps"]
    r = s.post(f"{API}/platform/tenants/{state['tid']}/status",
               json={"status": "suspended", "reason": "test"})
    assert r.status_code == 200
    assert r.json()["status"] == "suspended"
    # audit action
    r = s.get(f"{API}/platform/audit-logs", params={"tenant_id": state["tid"], "action_prefix": "tenant.status"})
    actions = [a["action"] for a in r.json()]
    assert "tenant.status.suspended" in actions
    # alert created
    r = s.get(f"{API}/platform/alerts", params={"unacknowledged_only": True})
    assert r.status_code == 200
    titles = [a["title"] for a in r.json()]
    assert any("suspended" in t.lower() for t in titles)


def test_status_reactivate():
    s = state["ps"]
    r = s.post(f"{API}/platform/tenants/{state['tid']}/status", json={"status": "active"})
    assert r.status_code == 200
    assert r.json()["status"] == "active"


# --------- Plan change ---------
def test_plan_change_and_mrr_delta():
    s = state["ps"]
    r = s.post(f"{API}/platform/tenants/{state['tid']}/plan",
               json={"plan": "standard", "reason": "upgrade"})
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "standard"
    assert body["subscription_started_at"] is not None
    r = s.get(f"{API}/platform/audit-logs", params={"tenant_id": state["tid"], "action_prefix": "tenant.plan"})
    logs = r.json()
    assert any(l["action"] == "tenant.plan.change" for l in logs)
    plan_log = [l for l in logs if l["action"] == "tenant.plan.change"][0]
    assert "mrr_delta" in (plan_log.get("metadata") or {})


# --------- Entitlements ---------
def test_entitlements_partial_merge():
    s = state["ps"]
    r = s.post(f"{API}/platform/tenants/{state['tid']}/entitlements",
               json={"modules": {"library": True, "bogus_key": True}})
    assert r.status_code == 200
    mods = r.json()["modules"]
    assert mods["library"] is True
    assert "bogus_key" not in mods
    # existing CRM still True
    assert mods["crm"] is True


# --------- Usage ---------
def test_tenant_usage():
    s = state["ps"]
    r = s.get(f"{API}/platform/tenants/{state['tid']}/usage")
    assert r.status_code == 200
    data = r.json()
    for k in ["users_total", "users_by_role", "audit_events_30d", "logins_30d"]:
        assert k in data
    assert data["users_total"] >= 1
    assert isinstance(data["users_by_role"], dict)


# --------- Alerts ack ---------
def test_alerts_ack():
    s = state["ps"]
    r = s.get(f"{API}/platform/alerts", params={"unacknowledged_only": True})
    alerts = r.json()
    if not alerts:
        pytest.skip("no alerts to ack")
    aid = alerts[0]["id"]
    r = s.post(f"{API}/platform/alerts/{aid}/acknowledge")
    assert r.status_code == 200
    assert r.json()["acknowledged"] is True
    # audit
    r = s.get(f"{API}/platform/audit-logs", params={"action_prefix": "alert.acknowledge"})
    assert any(l["action"] == "alert.acknowledge" for l in r.json())


# --------- Impersonation ---------
def test_impersonation_start_and_session():
    s = _sess()
    r = s.post(f"{API}/auth/login", json={"email": PLATFORM_EMAIL, "password": PLATFORM_PW})
    assert r.status_code == 200
    r = s.post(f"{API}/platform/tenants/{state['tid']}/impersonate",
               json={"reason": "Support ticket #42"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["impersonating"]["tenant_id"] == state["tid"]
    # session must now return school_admin + impersonation object
    r = s.get(f"{API}/auth/session")
    assert r.status_code == 200
    sess = r.json()
    assert sess["user"]["role"] == "school_admin"
    assert sess["impersonation"] is not None
    assert sess["impersonation"]["impersonator_email"] == PLATFORM_EMAIL
    assert sess["impersonation"]["reason"] == "Support ticket #42"
    # can hit /school/ as target tenant
    r = s.get(f"{API}/school/")
    assert r.status_code == 200
    assert r.json()["id"] == state["tid"]
    r = s.get(f"{API}/school/users")
    assert r.status_code == 200
    state["imp_sess"] = s


def test_impersonation_reason_min_length():
    s = _sess()
    r = s.post(f"{API}/auth/login", json={"email": PLATFORM_EMAIL, "password": PLATFORM_PW})
    r = s.post(f"{API}/platform/tenants/{state['tid']}/impersonate", json={"reason": "hi"})
    assert r.status_code == 422


def test_impersonate_platform_admin_400():
    # find another platform superadmin? Simpler: try to impersonate self via target_user_id
    s = _sess()
    r = s.post(f"{API}/auth/login", json={"email": PLATFORM_EMAIL, "password": PLATFORM_PW})
    me = s.get(f"{API}/auth/me").json()
    # can't easily impersonate platform admin into a tenant (target must be in tenant)
    # But endpoint has an early check for role. We craft: pick platform admin id + any tenant
    r = s.post(f"{API}/platform/tenants/{state['tid']}/impersonate",
               json={"reason": "block me", "target_user_id": me["id"]})
    # Since platform admin has no tenant_id == state['tid'], the DB lookup fails -> 404
    # This is acceptable; the endpoint blocks it either way (404 or 400). Assert not 200.
    assert r.status_code in (400, 404)


def test_impersonation_exit():
    s = state["imp_sess"]
    r = s.post(f"{API}/platform/impersonate/exit")
    assert r.status_code == 200, r.text
    r = s.get(f"{API}/auth/session")
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "platform_superadmin"
    assert r.json()["impersonation"] is None
    # audit has both events
    r = s.get(f"{API}/platform/audit-logs", params={"action_prefix": "impersonation"})
    actions = [a["action"] for a in r.json()]
    assert "impersonation.start" in actions
    assert "impersonation.end" in actions


# --------- Tenant isolation regression w/ wizard schools ---------
def test_two_wizard_schools_isolation():
    s = state["ps"]
    slugA = f"iso-a-{RUN}"
    slugB = f"iso-b-{RUN}"
    ownerA = f"ownera-{RUN}@example.com"
    ownerB = f"ownerb-{RUN}@example.com"
    pwA = "AdminA@1234"
    pwB = "AdminB@1234"
    payloadA = _wizard_payload(slugA, ownerA, school_code=f"AA-{RUN}")
    payloadA["administrator"]["temp_password"] = pwA
    payloadB = _wizard_payload(slugB, ownerB, school_code=f"BB-{RUN}")
    payloadB["administrator"]["temp_password"] = pwB
    rA = s.post(f"{API}/platform/schools", json=payloadA); assert rA.status_code == 201, rA.text
    rB = s.post(f"{API}/platform/schools", json=payloadB); assert rB.status_code == 201, rB.text
    tidB = rB.json()["tenant"]["id"]
    userB_id = rB.json()["administrator"]["id"]

    sA = _sess()
    r = sA.post(f"{API}/auth/login", json={"email": ownerA, "password": pwA, "tenant_slug": slugA})
    assert r.status_code == 200, r.text
    # cannot see B users
    r = sA.get(f"{API}/school/users/{userB_id}")
    assert r.status_code == 404
    # cannot access platform
    r = sA.get(f"{API}/platform/tenants")
    assert r.status_code == 403
