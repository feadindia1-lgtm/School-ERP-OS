"""Platform Super Admin endpoints — Prompt 1.

Covers:
  • Tenant CRUD via multi-step wizard
  • Lifecycle: activate / suspend / archive
  • Subscription plan changes
  • Feature entitlement (module toggles)
  • Tenant usage
  • Platform stats + dashboard
  • Recently onboarded schools
  • System alerts
  • Support-mode impersonation (start + exit) — every event audited
"""
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
import jwt

from app.api.v1.auth_routes import _tenant_to_out, _user_to_out
from app.api.v1.schemas import (
    AlertOut,
    AuditLogOut,
    CreateSchoolRequest,
    CreateSchoolResponse,
    ImpersonateRequest,
    PlatformStats,
    TenantEntitlementsUpdate,
    TenantOut,
    TenantPlanChange,
    TenantStatusChange,
    UpdateTenantRequest,
    UserOut,
)
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user, require_platform_admin
from app.core.permissions import (
    ROLE_PLATFORM_SUPERADMIN,
    ROLE_SCHOOL_ADMIN,
    ROLE_SCHOOL_OWNER,
    is_platform_role,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
)
from app.models.tenant import (
    DEFAULT_ACADEMIC,
    DEFAULT_BRANDING,
    DEFAULT_CONTACT,
    DEFAULT_MODULES,
    Tenant,
)
from app.models.user import User
from app.services.alert_service import create_alert
from app.services.audit_service import log_event
from app.services.pricing import PLAN_PRICING, mrr_from_tenants

router = APIRouter(prefix="/platform", tags=["platform"])


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Not found")


def _tenant_or_404(doc: dict | None) -> dict:
    if not doc:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return doc


# ============================================================
# Wizard: create a school
# ============================================================
@router.post("/schools", response_model=CreateSchoolResponse, status_code=201)
async def create_school(
    payload: CreateSchoolRequest,
    request: Request,
    user: dict = Depends(require_platform_admin()),
):
    db = get_db()

    if await db.tenants.find_one({"slug": payload.institution.slug}):
        raise HTTPException(status_code=409, detail="Slug already in use")
    if payload.institution.school_code and await db.tenants.find_one({"school_code": payload.institution.school_code}):
        raise HTTPException(status_code=409, detail="School code already in use")

    contact = {**DEFAULT_CONTACT, **payload.contact.model_dump(exclude_none=True)}
    academic = {**DEFAULT_ACADEMIC, **payload.academic.model_dump()}
    branding = {**DEFAULT_BRANDING, **payload.branding.model_dump()}
    modules = {**DEFAULT_MODULES, **payload.modules.model_dump()}

    trial_ends = None
    subscription_started = None
    now = datetime.now(timezone.utc).isoformat()
    if payload.plan == "trial":
        trial_ends = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    else:
        subscription_started = now

    tenant = Tenant(
        name=payload.institution.school_name,
        slug=payload.institution.slug,
        short_name=payload.institution.short_name,
        school_code=payload.institution.school_code,
        board=payload.institution.board,
        school_type=payload.institution.school_type,
        contact_email=payload.contact.email,
        contact_phone=payload.contact.phone,
        address=payload.contact.address_line,
        country=payload.contact.country,
        contact=contact,
        academic=academic,
        branding=branding,
        modules=modules,
        plan=payload.plan,
        status="trial" if payload.plan == "trial" else "active",
        trial_ends_at=trial_ends,
        subscription_started_at=subscription_started,
    )
    res = await db.tenants.insert_one(tenant.to_mongo())
    tenant_id = str(res.inserted_id)

    admin_email = payload.administrator.email.lower()
    if await db.users.find_one({"email": admin_email, "tenant_id": tenant_id}):
        # Impossible in a fresh tenant, but keep for safety
        raise HTTPException(status_code=409, detail="Administrator email conflict")

    generated_password = None
    admin_password = payload.administrator.temp_password
    if not admin_password:
        # Generate a temporary password when caller opted for invite flow.
        import secrets as _secrets
        admin_password = _secrets.token_urlsafe(9)
        generated_password = admin_password

    admin_doc = User(
        tenant_id=tenant_id,
        email=admin_email,
        password_hash=hash_password(admin_password),
        full_name=payload.administrator.full_name,
        role=ROLE_SCHOOL_ADMIN,
    ).to_mongo()
    admin_res = await db.users.insert_one(admin_doc)
    admin_id = str(admin_res.inserted_id)

    tenant_doc = await db.tenants.find_one({"_id": res.inserted_id})
    await log_event(
        action="school.create", resource="tenant", resource_id=tenant_id,
        tenant_id=tenant_id, actor=user, request=request,
        new_value={
            "name": tenant.name, "slug": tenant.slug, "plan": tenant.plan,
            "status": tenant.status, "board": tenant.board, "school_type": tenant.school_type,
        },
        metadata={"administrator_email": admin_email},
    )
    await log_event(
        action="user.create", resource="user", resource_id=admin_id,
        tenant_id=tenant_id, actor=user, request=request,
        new_value={"email": admin_email, "role": ROLE_SCHOOL_ADMIN},
    )
    await create_alert(
        title="New school onboarded",
        message=f"{tenant.name} ({tenant.slug}) was onboarded by {user['email']}.",
        level="info", resource="tenant", resource_id=tenant_id,
    )

    admin_user = _user_to_out(
        {"id": admin_id, "email": admin_email, "full_name": payload.administrator.full_name,
         "role": ROLE_SCHOOL_ADMIN, "status": "active"},
        tenant_id,
    )
    return CreateSchoolResponse(
        tenant=_tenant_to_out(tenant_doc),
        administrator=admin_user,
        temp_password=generated_password,
    )


# ============================================================
# List / Detail / Edit
# ============================================================
@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(
    status: str | None = None,
    q: str | None = None,
    _: dict = Depends(require_platform_admin()),
):
    query: dict = {}
    if status:
        query["status"] = status
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"slug": {"$regex": q, "$options": "i"}},
            {"school_code": {"$regex": q, "$options": "i"}},
        ]
    docs = await get_db().tenants.find(query).sort("created_at", -1).to_list(1000)
    return [_tenant_to_out(d) for d in docs]


@router.get("/tenants/{tenant_id}", response_model=TenantOut)
async def get_tenant(tenant_id: str, _: dict = Depends(require_platform_admin())):
    doc = await get_db().tenants.find_one({"_id": _oid(tenant_id)})
    return _tenant_to_out(_tenant_or_404(doc))


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: str,
    payload: UpdateTenantRequest,
    request: Request,
    user: dict = Depends(require_platform_admin()),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    db = get_db()
    oid = _oid(tenant_id)
    old = _tenant_or_404(await db.tenants.find_one({"_id": oid}))
    await db.tenants.update_one({"_id": oid}, {"$set": updates})
    new = await db.tenants.find_one({"_id": oid})
    await log_event(
        action="tenant.update", resource="tenant", resource_id=tenant_id,
        tenant_id=tenant_id, actor=user, request=request,
        old_value={k: old.get(k) for k in updates.keys()}, new_value=updates,
    )
    return _tenant_to_out(new)


# ============================================================
# Lifecycle
# ============================================================
@router.post("/tenants/{tenant_id}/status", response_model=TenantOut)
async def change_status(
    tenant_id: str,
    payload: TenantStatusChange,
    request: Request,
    user: dict = Depends(require_platform_admin()),
):
    db = get_db()
    oid = _oid(tenant_id)
    old = _tenant_or_404(await db.tenants.find_one({"_id": oid}))
    await db.tenants.update_one({"_id": oid}, {"$set": {"status": payload.status}})
    new = await db.tenants.find_one({"_id": oid})
    await log_event(
        action=f"tenant.status.{payload.status}", resource="tenant", resource_id=tenant_id,
        tenant_id=tenant_id, actor=user, request=request,
        old_value={"status": old.get("status")}, new_value={"status": payload.status},
        metadata={"reason": payload.reason},
    )
    if payload.status in {"suspended", "archived"}:
        await create_alert(
            title=f"School {payload.status}", level="warning",
            message=f"{new.get('name')} was {payload.status} by {user['email']}. Reason: {payload.reason or 'n/a'}",
            resource="tenant", resource_id=tenant_id, tenant_id=tenant_id,
        )
    return _tenant_to_out(new)


@router.post("/tenants/{tenant_id}/plan", response_model=TenantOut)
async def change_plan(
    tenant_id: str,
    payload: TenantPlanChange,
    request: Request,
    user: dict = Depends(require_platform_admin()),
):
    db = get_db()
    oid = _oid(tenant_id)
    old = _tenant_or_404(await db.tenants.find_one({"_id": oid}))
    updates = {"plan": payload.plan}
    if payload.plan != "trial" and not old.get("subscription_started_at"):
        updates["subscription_started_at"] = datetime.now(timezone.utc).isoformat()
    await db.tenants.update_one({"_id": oid}, {"$set": updates})
    new = await db.tenants.find_one({"_id": oid})
    await log_event(
        action="tenant.plan.change", resource="tenant", resource_id=tenant_id,
        tenant_id=tenant_id, actor=user, request=request,
        old_value={"plan": old.get("plan")}, new_value={"plan": payload.plan},
        metadata={"reason": payload.reason, "mrr_delta": PLAN_PRICING.get(payload.plan, 0) - PLAN_PRICING.get(old.get("plan", "trial"), 0)},
    )
    return _tenant_to_out(new)


@router.post("/tenants/{tenant_id}/entitlements", response_model=TenantOut)
async def update_entitlements(
    tenant_id: str,
    payload: TenantEntitlementsUpdate,
    request: Request,
    user: dict = Depends(require_platform_admin()),
):
    db = get_db()
    oid = _oid(tenant_id)
    old = _tenant_or_404(await db.tenants.find_one({"_id": oid}))
    current = old.get("modules") or dict(DEFAULT_MODULES)
    # Only accept known module keys
    accepted = {k: bool(v) for k, v in payload.modules.items() if k in DEFAULT_MODULES}
    new_modules = {**current, **accepted}
    await db.tenants.update_one({"_id": oid}, {"$set": {"modules": new_modules}})
    new = await db.tenants.find_one({"_id": oid})
    await log_event(
        action="tenant.entitlements.update", resource="tenant", resource_id=tenant_id,
        tenant_id=tenant_id, actor=user, request=request,
        old_value={"modules": current}, new_value={"modules": new_modules},
    )
    return _tenant_to_out(new)


# ============================================================
# Usage
# ============================================================
@router.get("/tenants/{tenant_id}/usage")
async def tenant_usage(tenant_id: str, _: dict = Depends(require_platform_admin())):
    db = get_db()
    _tenant_or_404(await db.tenants.find_one({"_id": _oid(tenant_id)}))
    users_total = await db.users.count_documents({"tenant_id": tenant_id})
    users_by_role = {}
    async for doc in db.users.aggregate([
        {"$match": {"tenant_id": tenant_id}},
        {"$group": {"_id": "$role", "count": {"$sum": 1}}},
    ]):
        users_by_role[doc["_id"]] = doc["count"]

    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    audit_30d = await db.audit_logs.count_documents({
        "tenant_id": tenant_id, "created_at": {"$gte": thirty_days_ago},
    })
    logins_30d = await db.audit_logs.count_documents({
        "tenant_id": tenant_id, "action": "auth.login", "created_at": {"$gte": thirty_days_ago},
    })
    return {
        "users_total": users_total,
        "users_by_role": users_by_role,
        "audit_events_30d": audit_30d,
        "logins_30d": logins_30d,
    }


# ============================================================
# Audit & Stats
# ============================================================
@router.get("/audit-logs", response_model=list[AuditLogOut])
async def platform_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    tenant_id: str | None = None,
    action_prefix: str | None = None,
    _: dict = Depends(require_platform_admin()),
):
    q: dict = {}
    if tenant_id:
        q["tenant_id"] = tenant_id
    if action_prefix:
        q["action"] = {"$regex": f"^{action_prefix}"}
    docs = await get_db().audit_logs.find(q).sort("created_at", -1).to_list(limit)
    return [
        AuditLogOut(
            id=str(d["_id"]),
            tenant_id=d.get("tenant_id"),
            actor_id=d.get("actor_id"),
            actor_email=d.get("actor_email"),
            actor_role=d.get("actor_role"),
            action=d["action"],
            resource=d["resource"],
            resource_id=d.get("resource_id"),
            ip=d.get("ip"),
            created_at=d["created_at"],
            metadata=d.get("metadata") or {},
        )
        for d in docs
    ]


@router.get("/stats", response_model=PlatformStats)
async def platform_stats(_: dict = Depends(require_platform_admin())):
    db = get_db()
    tenants = await db.tenants.find().to_list(10000)
    counts = {"active": 0, "trial": 0, "suspended": 0, "archived": 0}
    for t in tenants:
        counts[t.get("status", "active")] = counts.get(t.get("status", "active"), 0) + 1

    # Roles that count as students / teachers (placeholders — future prompts will add dedicated collections).
    total_students = await db.users.count_documents({"role": "student"})
    total_teachers = await db.users.count_documents({"role": {"$in": ["teacher", "class_teacher"]}})
    total_users = await db.users.count_documents({})

    thirty = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    audit_30d = await db.audit_logs.count_documents({"created_at": {"$gte": thirty}})
    open_alerts = await db.alerts.count_documents({"acknowledged": False})

    recent_docs = await db.tenants.find().sort("created_at", -1).to_list(5)
    recent = [_tenant_to_out(d) for d in recent_docs]

    subscription_status = {p: 0 for p in PLAN_PRICING.keys()}
    for t in tenants:
        p = t.get("plan", "trial")
        subscription_status[p] = subscription_status.get(p, 0) + 1

    return PlatformStats(
        total_schools=len(tenants),
        active_schools=counts.get("active", 0),
        trial_schools=counts.get("trial", 0),
        suspended_schools=counts.get("suspended", 0),
        archived_schools=counts.get("archived", 0),
        total_students=total_students,
        total_teachers=total_teachers,
        total_users=total_users,
        mrr=mrr_from_tenants(tenants),
        audit_events_30d=audit_30d,
        subscription_status=subscription_status,
        recently_onboarded=recent,
        open_alerts=open_alerts,
    )


# ============================================================
# Alerts
# ============================================================
@router.get("/alerts", response_model=list[AlertOut])
async def list_alerts(
    unacknowledged_only: bool = False,
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(require_platform_admin()),
):
    q: dict = {}
    if unacknowledged_only:
        q["acknowledged"] = False
    docs = await get_db().alerts.find(q).sort("created_at", -1).to_list(limit)
    return [
        AlertOut(
            id=str(d["_id"]), tenant_id=d.get("tenant_id"), level=d.get("level", "info"),
            title=d["title"], message=d["message"], resource=d.get("resource"),
            resource_id=d.get("resource_id"), acknowledged=bool(d.get("acknowledged", False)),
            created_at=d["created_at"],
        )
        for d in docs
    ]


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertOut)
async def ack_alert(alert_id: str, request: Request, user: dict = Depends(require_platform_admin())):
    db = get_db()
    oid = _oid(alert_id)
    doc = await db.alerts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.alerts.update_one({"_id": oid}, {"$set": {"acknowledged": True}})
    doc = await db.alerts.find_one({"_id": oid})
    await log_event(
        action="alert.acknowledge", resource="alert", resource_id=alert_id,
        actor=user, request=request, tenant_id=doc.get("tenant_id"),
    )
    return AlertOut(
        id=str(doc["_id"]), tenant_id=doc.get("tenant_id"), level=doc.get("level", "info"),
        title=doc["title"], message=doc["message"], resource=doc.get("resource"),
        resource_id=doc.get("resource_id"), acknowledged=True, created_at=doc["created_at"],
    )


# ============================================================
# Impersonation — "Support mode".  Every event audited.
# ============================================================
IMPERSONATOR_COOKIE = "impersonator_id"


def _set_cookie(response: Response, key: str, value: str, max_age: int) -> None:
    response.set_cookie(
        key, value, httponly=True, secure=True, samesite="none",
        max_age=max_age, path="/",
    )


@router.post("/tenants/{tenant_id}/impersonate")
async def start_impersonation(
    tenant_id: str,
    payload: ImpersonateRequest,
    request: Request,
    response: Response,
    user: dict = Depends(require_platform_admin()),
):
    db = get_db()
    tenant = _tenant_or_404(await db.tenants.find_one({"_id": _oid(tenant_id)}))

    if payload.target_user_id:
        target = await db.users.find_one({
            "_id": _oid(payload.target_user_id), "tenant_id": tenant_id,
        })
    else:
        target = await db.users.find_one({
            "tenant_id": tenant_id, "role": ROLE_SCHOOL_OWNER,
        }) or await db.users.find_one({
            "tenant_id": tenant_id, "role": ROLE_SCHOOL_ADMIN,
        })
    if not target:
        raise HTTPException(status_code=404, detail="No suitable school user to impersonate")
    if target.get("role") == ROLE_PLATFORM_SUPERADMIN:
        raise HTTPException(status_code=400, detail="Cannot impersonate a platform superadmin")

    target_id = str(target["_id"])
    access = create_access_token(
        user_id=target_id, tenant_id=tenant_id, role=target["role"],
        extra={"impersonated_by": user["id"], "impersonation_reason": payload.reason},
    )
    refresh, jti, expires = create_refresh_token(user_id=target_id, tenant_id=tenant_id)
    await db.refresh_tokens.insert_one({
        "jti": jti, "user_id": target_id, "tenant_id": tenant_id, "expires_at": expires,
        "impersonated_by": user["id"],
    })
    _set_cookie(response, "access_token", access, settings.ACCESS_TOKEN_MINUTES * 60)
    _set_cookie(response, "refresh_token", refresh, settings.REFRESH_TOKEN_DAYS * 86400)
    _set_cookie(response, IMPERSONATOR_COOKIE, user["id"], 3600)

    await log_event(
        action="impersonation.start", resource="user", resource_id=target_id,
        tenant_id=tenant_id, actor=user, request=request,
        metadata={"reason": payload.reason, "target_email": target.get("email"),
                  "target_role": target.get("role"), "school": tenant.get("name")},
    )
    await create_alert(
        title="Impersonation started", level="warning",
        message=f"{user['email']} started support mode as {target.get('email')} on {tenant.get('name')} — reason: {payload.reason}",
        resource="tenant", resource_id=tenant_id, tenant_id=tenant_id,
    )

    return {
        "ok": True,
        "impersonating": {
            "target_user_id": target_id,
            "target_email": target.get("email"),
            "tenant_id": tenant_id,
            "tenant_name": tenant.get("name"),
            "reason": payload.reason,
        },
    }


@router.post("/impersonate/exit")
async def exit_impersonation(
    request: Request, response: Response,
    user: dict = Depends(get_current_user),
):
    impersonator_id = request.cookies.get(IMPERSONATOR_COOKIE)
    if not impersonator_id:
        raise HTTPException(status_code=400, detail="No active impersonation")
    # Also verify JWT carries the impersonation claim
    if not user.get("impersonated_by") or user["impersonated_by"] != impersonator_id:
        raise HTTPException(status_code=403, detail="Impersonation cookie mismatch")

    db = get_db()
    platform_user = await db.users.find_one({"_id": _oid(impersonator_id)})
    if not platform_user or platform_user.get("role") != ROLE_PLATFORM_SUPERADMIN:
        raise HTTPException(status_code=403, detail="Impersonator no longer valid")

    plat_id = str(platform_user["_id"])
    access = create_access_token(user_id=plat_id, tenant_id=None, role=ROLE_PLATFORM_SUPERADMIN)
    refresh, jti, expires = create_refresh_token(user_id=plat_id, tenant_id=None)
    await db.refresh_tokens.insert_one({
        "jti": jti, "user_id": plat_id, "tenant_id": None, "expires_at": expires,
    })
    _set_cookie(response, "access_token", access, settings.ACCESS_TOKEN_MINUTES * 60)
    _set_cookie(response, "refresh_token", refresh, settings.REFRESH_TOKEN_DAYS * 86400)
    response.delete_cookie(IMPERSONATOR_COOKIE, path="/")

    await log_event(
        action="impersonation.end", resource="user", resource_id=user["id"],
        tenant_id=user.get("tenant_id"),
        actor={"id": plat_id, "email": platform_user["email"], "role": ROLE_PLATFORM_SUPERADMIN},
        request=request,
        metadata={"exited_from": user.get("email"), "reason": user.get("impersonation_reason")},
    )
    return {"ok": True}
