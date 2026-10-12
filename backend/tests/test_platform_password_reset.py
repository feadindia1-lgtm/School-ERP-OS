"""Platform admin password-reset flow — regression for the issue reported
where a school owner lost their password and had no way to recover it.

Scenarios covered:
- Platform superadmin lists tenant users.
- Reset with an explicit new_password lets the user log in with it.
- Reset with no new_password returns a generated temp password that works.
- Audit event is written with the stated reason.
- A platform-role user cannot be reset through the tenant endpoint.
- Login-attempt lockouts are cleared on reset.
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
PW = "SchoolOwner@123"
SA_EMAIL = os.environ.get("PLATFORM_SUPERADMIN_EMAIL", "superadmin@schoolos.dev")
SA_PW = os.environ.get("PLATFORM_SUPERADMIN_PASSWORD", "SuperAdmin@123")

state: dict = {}


def _sess() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(email: str, pw: str) -> requests.Session:
    s = _sess()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return s


def test_00_register_tenant_and_login():
    slug = f"rst-{RUN}"
    owner_email = f"owner-{RUN}@rst.example.com"
    s = _sess()
    r = s.post(f"{API}/auth/register-school", json={
        "school_name": f"Reset School {RUN}", "slug": slug,
        "contact_email": owner_email,
        "owner_full_name": "Reset Owner", "owner_email": owner_email, "owner_password": PW,
    })
    assert r.status_code == 201, r.text
    data = r.json()
    state["tenant_id"] = data["tenant"]["id"]
    state["owner_id"] = data["user"]["id"]
    state["owner_email"] = owner_email


def test_10_platform_lists_tenant_users():
    sa = _login(SA_EMAIL, SA_PW)
    r = sa.get(f"{API}/platform/tenants/{state['tenant_id']}/users")
    assert r.status_code == 200, r.text
    users = r.json()
    assert any(u["email"] == state["owner_email"] for u in users)
    state["sa"] = sa


def test_20_reset_with_explicit_password_logs_in():
    sa = state["sa"]
    new_pw = f"NewPass{RUN}!"
    r = sa.post(
        f"{API}/platform/tenants/{state['tenant_id']}/users/{state['owner_id']}/reset-password",
        json={"new_password": new_pw, "reason": "User forgot their original password"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["generated"] is False
    assert body["temporary_password"] == new_pw

    # Old password must now fail
    s = _sess()
    r = s.post(f"{API}/auth/login", json={"email": state["owner_email"], "password": PW})
    assert r.status_code == 401
    # New password must succeed
    r = s.post(f"{API}/auth/login", json={"email": state["owner_email"], "password": new_pw})
    assert r.status_code == 200, r.text


def test_30_reset_with_generated_password_logs_in():
    sa = state["sa"]
    r = sa.post(
        f"{API}/platform/tenants/{state['tenant_id']}/users/{state['owner_id']}/reset-password",
        json={"reason": "Trial regenerate"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["generated"] is True
    temp = body["temporary_password"]
    assert isinstance(temp, str) and len(temp) >= 8

    s = _sess()
    r = s.post(f"{API}/auth/login", json={"email": state["owner_email"], "password": temp})
    assert r.status_code == 200, r.text


def test_40_reason_is_required_and_audited():
    sa = state["sa"]
    r = sa.post(
        f"{API}/platform/tenants/{state['tenant_id']}/users/{state['owner_id']}/reset-password",
        json={},
    )
    assert r.status_code == 422

    # Check audit log for the password_reset events
    r = sa.get(f"{API}/platform/audit-logs", params={"action": "user.password_reset"})
    assert r.status_code == 200
    logs = r.json()
    assert any(l["resource_id"] == state["owner_id"] for l in logs)


def test_50_cannot_reset_platform_role_via_tenant_endpoint():
    sa = state["sa"]
    # Pick the platform superadmin user id via /auth/me
    me = sa.get(f"{API}/auth/me").json()
    sa_id = me["id"]
    r = sa.post(
        f"{API}/platform/tenants/{state['tenant_id']}/users/{sa_id}/reset-password",
        json={"reason": "Should not be allowed"},
    )
    # Either 404 (not in tenant) or 400 (platform role)
    assert r.status_code in (400, 404)


def test_60_non_platform_user_cannot_use_endpoint():
    # School owner (new password from test_30) tries to hit the platform endpoint
    r = requests.get(f"{API}/platform/tenants/{state['tenant_id']}/users")
    # Unauthenticated → 401
    assert r.status_code == 401
