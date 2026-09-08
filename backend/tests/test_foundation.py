"""Foundation tests for School OS: auth, tenant isolation, RBAC, audit, platform."""
import os
import time
import uuid

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://schoolos-foundation-1.preview.emergentagent.com"
API = f"{BASE}/api/v1"

RUN = uuid.uuid4().hex[:6]
RIVERSIDE_SLUG = f"riverside-{RUN}"
HILLTOP_SLUG = f"hilltop-{RUN}"
RIVERSIDE_EMAIL = f"owner-{RUN}@riverside.example.com"
HILLTOP_EMAIL = f"owner-{RUN}@hilltop.example.com"
OWNER_PW = "SchoolOwner@123"

state = {}


def _sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Meta / Health ----------
def test_health():
    r = requests.get(f"{BASE}/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["database"] == "up"


def test_meta():
    r = requests.get(f"{API}/meta")
    assert r.status_code == 200
    data = r.json()
    assert len(data["roles"]) == 11
    assert len(data["permissions"]) == 24


# ---------- Registration ----------
def test_register_riverside():
    s = _sess()
    r = s.post(f"{API}/auth/register-school", json={
        "school_name": "Riverside Academy",
        "slug": RIVERSIDE_SLUG,
        "contact_email": f"admin-{RUN}@riverside.example.com",
        "country": "US",
        "owner_full_name": "Ada Owner",
        "owner_email": RIVERSIDE_EMAIL,
        "owner_password": OWNER_PW,
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["user"]["role"] == "school_owner"
    assert data["tenant"]["slug"] == RIVERSIDE_SLUG
    # Cookies set
    assert "access_token" in s.cookies
    assert "refresh_token" in s.cookies
    state["riverside_session"] = s
    state["riverside_tenant_id"] = data["tenant"]["id"]
    state["riverside_owner_id"] = data["user"]["id"]


def test_register_hilltop():
    s = _sess()
    r = s.post(f"{API}/auth/register-school", json={
        "school_name": "Hilltop School",
        "slug": HILLTOP_SLUG,
        "contact_email": f"admin-{RUN}@hilltop.example.com",
        "owner_full_name": "Bob Owner",
        "owner_email": HILLTOP_EMAIL,
        "owner_password": "HillOwner@123",
    })
    assert r.status_code == 201, r.text
    data = r.json()
    state["hilltop_session"] = s
    state["hilltop_tenant_id"] = data["tenant"]["id"]
    state["hilltop_owner_id"] = data["user"]["id"]


def test_duplicate_slug_conflict():
    r = requests.post(f"{API}/auth/register-school", json={
        "school_name": "Dup",
        "slug": RIVERSIDE_SLUG,
        "contact_email": f"x-{RUN}@ex.example.com",
        "owner_full_name": "X Y",
        "owner_email": f"x-{RUN}@dup.example.com",
        "owner_password": "Password@123",
    })
    assert r.status_code == 409
    body = r.json()
    assert body["error"]["code"] == "conflict"


# ---------- Login ----------
def test_login_wrong_password():
    r = requests.post(f"{API}/auth/login", json={
        "email": RIVERSIDE_EMAIL, "password": "wrongpass", "tenant_slug": RIVERSIDE_SLUG,
    })
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_login_correct_returns_cookies():
    s = _sess()
    r = s.post(f"{API}/auth/login", json={
        "email": RIVERSIDE_EMAIL, "password": OWNER_PW, "tenant_slug": RIVERSIDE_SLUG,
    })
    assert r.status_code == 200
    assert "access_token" in s.cookies
    data = r.json()
    assert data["user"]["email"] == RIVERSIDE_EMAIL


def test_brute_force_lockout():
    # Use a fresh non-existent email to isolate lockout counter
    victim = f"brute-{RUN}@riverside.example.com"
    for i in range(5):
        r = requests.post(f"{API}/auth/login", json={
            "email": victim, "password": "bad", "tenant_slug": RIVERSIDE_SLUG,
        })
        assert r.status_code == 401
    # 6th attempt should be 429
    r = requests.post(f"{API}/auth/login", json={
        "email": victim, "password": "bad", "tenant_slug": RIVERSIDE_SLUG,
    })
    assert r.status_code == 429, f"Expected lockout but got {r.status_code}: {r.text}"


# ---------- Me / Refresh / Logout ----------
def test_me_returns_permissions():
    s = state["riverside_session"]
    r = s.get(f"{API}/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == RIVERSIDE_EMAIL
    assert "user.create" in data["permissions"]


def test_refresh():
    s = state["riverside_session"]
    old_access = s.cookies.get("access_token")
    time.sleep(1)
    r = s.post(f"{API}/auth/refresh")
    assert r.status_code == 200
    new_access = s.cookies.get("access_token")
    assert new_access and new_access != old_access


def test_logout_clears_and_invalidates():
    s = _sess()
    r = s.post(f"{API}/auth/login", json={
        "email": RIVERSIDE_EMAIL, "password": OWNER_PW, "tenant_slug": RIVERSIDE_SLUG,
    })
    assert r.status_code == 200
    r = s.post(f"{API}/auth/logout")
    assert r.status_code == 200
    # After logout, /me should be 401
    r = s.get(f"{API}/auth/me")
    assert r.status_code == 401


# ---------- Platform Superadmin ----------
def test_platform_superadmin_login_and_endpoints():
    s = _sess()
    r = s.post(f"{API}/auth/login", json={
        "email": "superadmin@schoolos.dev", "password": "SuperAdmin@123",
    })
    assert r.status_code == 200, r.text
    state["platform_session"] = s

    r = s.get(f"{API}/platform/tenants")
    assert r.status_code == 200
    tenants = r.json()
    slugs = [t["slug"] for t in tenants]
    assert RIVERSIDE_SLUG in slugs and HILLTOP_SLUG in slugs

    r = s.get(f"{API}/platform/stats")
    assert r.status_code == 200
    stats = r.json()
    assert "total_schools" in stats and "total_users" in stats and "audit_events_30d" in stats


def test_platform_patch_tenant_audit():
    s = state["platform_session"]
    tid = state["hilltop_tenant_id"]
    r = s.patch(f"{API}/platform/tenants/{tid}", json={"plan": "pro", "status": "active"})
    assert r.status_code == 200
    assert r.json()["plan"] == "pro"
    # audit
    r = s.get(f"{API}/platform/audit-logs", params={"tenant_id": tid})
    assert r.status_code == 200
    actions = [a["action"] for a in r.json()]
    assert "tenant.update" in actions


# ---------- Tenant Isolation ----------
def test_tenant_isolation_users_list():
    s = state["riverside_session"]
    # Re-login since previous logout test used same email; state session may still be valid actually since logout test used a new session. Ensure by calling /me:
    r = s.get(f"{API}/auth/me")
    if r.status_code != 200:
        # re-login
        r = s.post(f"{API}/auth/login", json={
            "email": RIVERSIDE_EMAIL, "password": OWNER_PW, "tenant_slug": RIVERSIDE_SLUG,
        })
        assert r.status_code == 200
    r = s.get(f"{API}/school/users")
    assert r.status_code == 200
    users = r.json()
    tenant_ids = {u["tenant_id"] for u in users}
    assert tenant_ids == {state["riverside_tenant_id"]}


def test_tenant_isolation_cross_access_404():
    s = state["riverside_session"]
    hilltop_uid = state["hilltop_owner_id"]
    r = s.get(f"{API}/school/users/{hilltop_uid}")
    assert r.status_code == 404


def test_school_owner_denied_platform():
    s = state["riverside_session"]
    r = s.get(f"{API}/platform/tenants")
    assert r.status_code == 403


def test_school_self_only():
    s = state["riverside_session"]
    r = s.get(f"{API}/school/")
    assert r.status_code == 200
    assert r.json()["slug"] == RIVERSIDE_SLUG


# ---------- RBAC ----------
def test_owner_can_create_teacher():
    s = state["riverside_session"]
    r = s.post(f"{API}/school/users", json={
        "email": f"teacher-{RUN}@riverside.example.com",
        "password": "Teacher@1234",
        "full_name": "T Teacher",
        "role": "teacher",
    })
    assert r.status_code == 201, r.text
    state["teacher_email"] = f"teacher-{RUN}@riverside.example.com"
    state["teacher_id"] = r.json()["id"]


def test_teacher_cannot_create_user():
    s = _sess()
    r = s.post(f"{API}/auth/login", json={
        "email": state["teacher_email"], "password": "Teacher@1234",
        "tenant_slug": RIVERSIDE_SLUG,
    })
    assert r.status_code == 200
    state["teacher_session"] = s
    r = s.post(f"{API}/school/users", json={
        "email": f"t2-{RUN}@riverside.example.com",
        "password": "Whatever@1234",
        "full_name": "X",
        "role": "teacher",
    })
    assert r.status_code == 403
    assert "user.create" in r.json()["error"]["message"]


def test_create_platform_role_forbidden():
    s = state["riverside_session"]
    r = s.post(f"{API}/school/users", json={
        "email": f"pa-{RUN}@riverside.example.com",
        "password": "Password@1234",
        "full_name": "PA",
        "role": "platform_superadmin",
    })
    assert r.status_code == 400


# ---------- Audit ----------
def test_audit_events_on_register_and_create():
    s = state["platform_session"]
    tid = state["riverside_tenant_id"]
    r = s.get(f"{API}/platform/audit-logs", params={"tenant_id": tid, "limit": 200})
    assert r.status_code == 200
    logs = r.json()
    actions = {log["action"] for log in logs}
    assert "tenant.create" in actions
    assert "auth.register" in actions
    assert "user.create" in actions
    # Check fields
    for log in logs:
        assert "actor_id" in log and "actor_email" in log
        assert "created_at" in log
        assert "ip" in log


def test_school_audit_permission():
    # Teacher forbidden
    s = state["teacher_session"]
    r = s.get(f"{API}/school/audit-logs")
    assert r.status_code == 403
    # Owner allowed
    s = state["riverside_session"]
    r = s.get(f"{API}/school/audit-logs")
    assert r.status_code == 200


# ---------- Error envelope ----------
def test_validation_error_envelope():
    r = requests.post(f"{API}/auth/register-school", json={"slug": "x"})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["details"], list)


def test_401_envelope():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"
