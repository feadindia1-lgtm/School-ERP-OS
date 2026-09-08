"""Platform Super Admin endpoints — manage tenants and view platform-wide audit."""
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.auth_routes import _tenant_to_out
from app.api.v1.schemas import AuditLogOut, TenantOut, UpdateTenantRequest
from app.core.db import get_db
from app.core.deps import require_platform_admin
from app.services.audit_service import log_event

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(_: dict = Depends(require_platform_admin())):
    docs = await get_db().tenants.find().sort("created_at", -1).to_list(1000)
    return [_tenant_to_out(d) for d in docs]


@router.get("/tenants/{tenant_id}", response_model=TenantOut)
async def get_tenant(tenant_id: str, _: dict = Depends(require_platform_admin())):
    try:
        oid = ObjectId(tenant_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Tenant not found")
    doc = await get_db().tenants.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _tenant_to_out(doc)


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: str,
    payload: UpdateTenantRequest,
    request: Request,
    user: dict = Depends(require_platform_admin()),
):
    try:
        oid = ObjectId(tenant_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Tenant not found")
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    db = get_db()
    old = await db.tenants.find_one({"_id": oid})
    if not old:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await db.tenants.update_one({"_id": oid}, {"$set": updates})
    new = await db.tenants.find_one({"_id": oid})
    await log_event(
        action="tenant.update", resource="tenant", resource_id=tenant_id,
        tenant_id=tenant_id, actor=user, request=request,
        old_value={k: old.get(k) for k in updates.keys()}, new_value=updates,
    )
    return _tenant_to_out(new)


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def platform_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    tenant_id: str | None = None,
    _: dict = Depends(require_platform_admin()),
):
    q: dict = {}
    if tenant_id:
        q["tenant_id"] = tenant_id
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
        )
        for d in docs
    ]


@router.get("/stats")
async def platform_stats(_: dict = Depends(require_platform_admin())):
    db = get_db()
    return {
        "tenants": await db.tenants.count_documents({}),
        "active_tenants": await db.tenants.count_documents({"status": "active"}),
        "users": await db.users.count_documents({}),
        "audit_events": await db.audit_logs.count_documents({}),
    }
