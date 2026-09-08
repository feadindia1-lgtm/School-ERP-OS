"""Audit log entry."""
from pydantic import Field

from app.models.base import BaseDocument


class AuditLog(BaseDocument):
    tenant_id: str | None = None  # None for platform-level events
    actor_id: str | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    action: str  # e.g. "user.create", "auth.login"
    resource: str  # e.g. "user", "tenant"
    resource_id: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    old_value: dict | None = None
    new_value: dict | None = None
    metadata: dict = Field(default_factory=dict)
