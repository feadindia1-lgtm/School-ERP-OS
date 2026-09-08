"""Central helper to write audit log entries."""
from fastapi import Request

from app.core.db import get_db
from app.models.audit import AuditLog


async def log_event(
    *,
    action: str,
    resource: str,
    resource_id: str | None = None,
    tenant_id: str | None = None,
    actor: dict | None = None,
    request: Request | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    metadata: dict | None = None,
) -> None:
    ip = None
    user_agent = None
    if request is not None:
        client = request.client
        xff = request.headers.get("x-forwarded-for")
        ip = (xff.split(",")[0].strip() if xff else (client.host if client else None))
        user_agent = request.headers.get("user-agent")

    entry = AuditLog(
        tenant_id=tenant_id,
        actor_id=(actor or {}).get("id"),
        actor_email=(actor or {}).get("email"),
        actor_role=(actor or {}).get("role"),
        action=action,
        resource=resource,
        resource_id=resource_id,
        ip=ip,
        user_agent=user_agent,
        old_value=old_value,
        new_value=new_value,
        metadata=metadata or {},
    )
    await get_db().audit_logs.insert_one(entry.to_mongo())
