"""School-scoped endpoints for tenant users.

Every query is filtered by tenant_id derived from the authenticated user's
token — clients cannot pass tenant_id in the URL and access another school.
"""
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.auth_routes import _tenant_to_out, _user_to_out
from app.api.v1.schemas import (
    AuditLogOut,
    CreateUserRequest,
    TenantOut,
    UpdateTenantRequest,
    UpdateUserRequest,
    UserOut,
)
from app.core.db import get_db
from app.core.deps import require_permission, require_tenant_user
from app.core.permissions import (
    ALL_PERMISSIONS,
    ALL_ROLES,
    P_AUDIT_VIEW_SCHOOL,
    P_ROLE_ASSIGN,
    P_SCHOOL_EDIT,
    P_SCHOOL_VIEW,
    P_USER_CREATE,
    P_USER_DELETE,
    P_USER_EDIT,
    P_USER_VIEW,
    ROLE_PERMISSIONS,
    ROLE_PLATFORM_SUPERADMIN,
    permissions_for,
)
from app.core.security import hash_password
from app.models.user import User
from app.services.audit_service import log_event

router = APIRouter(prefix="/school", tags=["school"])


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Not found")


# ---------- School (self) ----------
@router.get("/", response_model=TenantOut)
async def get_own_school(user: dict = Depends(require_permission(P_SCHOOL_VIEW))):
    doc = await get_db().tenants.find_one({"_id": _oid(user["tenant_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="School not found")
    return _tenant_to_out(doc)


@router.patch("/", response_model=TenantOut)
async def update_own_school(
    payload: UpdateTenantRequest,
    request: Request,
    user: dict = Depends(require_permission(P_SCHOOL_EDIT)),
):
    updates = payload.model_dump(exclude_none=True)
    # Tenant users cannot change plan/status of their own school.
    updates.pop("status", None)
    updates.pop("plan", None)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    db = get_db()
    tid = _oid(user["tenant_id"])
    old = await db.tenants.find_one({"_id": tid})
    await db.tenants.update_one({"_id": tid}, {"$set": updates})
    new = await db.tenants.find_one({"_id": tid})
    await log_event(
        action="school.update", resource="tenant", resource_id=user["tenant_id"],
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={k: old.get(k) for k in updates.keys()}, new_value=updates,
    )
    return _tenant_to_out(new)


# ---------- Users within school ----------
@router.get("/users", response_model=list[UserOut])
async def list_users(user: dict = Depends(require_permission(P_USER_VIEW))):
    docs = await get_db().users.find({"tenant_id": user["tenant_id"]}).sort("created_at", -1).to_list(1000)
    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        d.pop("password_hash", None)
        out.append(_user_to_out(d, user["tenant_id"]))
    return out


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    payload: CreateUserRequest,
    request: Request,
    user: dict = Depends(require_permission(P_USER_CREATE)),
):
    if payload.role == ROLE_PLATFORM_SUPERADMIN or payload.role not in ALL_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    db = get_db()
    email = payload.email.lower()
    if await db.users.find_one({"email": email, "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=409, detail="Email already used in this school")

    doc = User(
        tenant_id=user["tenant_id"],
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    ).to_mongo()
    res = await db.users.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    await log_event(
        action="user.create", resource="user", resource_id=doc["id"],
        tenant_id=user["tenant_id"], actor=user, request=request,
        new_value={"email": email, "role": payload.role},
    )
    return _user_to_out(doc, user["tenant_id"])


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: str, user: dict = Depends(require_permission(P_USER_VIEW))):
    d = await get_db().users.find_one({"_id": _oid(user_id), "tenant_id": user["tenant_id"]})
    if not d:
        raise HTTPException(status_code=404, detail="User not found")
    d["id"] = str(d.pop("_id"))
    d.pop("password_hash", None)
    return _user_to_out(d, user["tenant_id"])


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    request: Request,
    user: dict = Depends(require_permission(P_USER_EDIT)),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "role" in updates:
        if updates["role"] == ROLE_PLATFORM_SUPERADMIN or updates["role"] not in ALL_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        if P_ROLE_ASSIGN not in (permissions_for(user["role"]) | set(user.get("extra_permissions", []))):
            raise HTTPException(status_code=403, detail="Missing permission: role.assign")
    db = get_db()
    old = await db.users.find_one({"_id": _oid(user_id), "tenant_id": user["tenant_id"]})
    if not old:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.users.find_one({"_id": old["_id"]})
    new["id"] = str(new.pop("_id"))
    new.pop("password_hash", None)
    await log_event(
        action="user.update", resource="user", resource_id=user_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={k: old.get(k) for k in updates.keys()}, new_value=updates,
    )
    return _user_to_out(new, user["tenant_id"])


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str, request: Request,
    user: dict = Depends(require_permission(P_USER_DELETE)),
):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db = get_db()
    target = await db.users.find_one({"_id": _oid(user_id), "tenant_id": user["tenant_id"]})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.delete_one({"_id": target["_id"]})
    await log_event(
        action="user.delete", resource="user", resource_id=user_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={"email": target.get("email"), "role": target.get("role")},
    )
    return {"ok": True}


# ---------- RBAC metadata ----------
@router.get("/rbac")
async def rbac_catalog(_: dict = Depends(require_tenant_user())):
    return {
        "roles": [r for r in ALL_ROLES if r != ROLE_PLATFORM_SUPERADMIN],
        "permissions": ALL_PERMISSIONS,
        "role_permissions": {
            r: sorted(list(perms))
            for r, perms in ROLE_PERMISSIONS.items()
            if r != ROLE_PLATFORM_SUPERADMIN
        },
    }


# ---------- Audit ----------
@router.get("/audit-logs", response_model=list[AuditLogOut])
async def school_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(require_permission(P_AUDIT_VIEW_SCHOOL)),
):
    docs = await get_db().audit_logs.find({"tenant_id": user["tenant_id"]}).sort("created_at", -1).to_list(limit)
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
        )
        for d in docs
    ]
