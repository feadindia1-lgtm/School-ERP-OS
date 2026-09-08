"""User domain model.

`tenant_id` is `None` for platform-level users (Platform Super Admin).
All other users belong to exactly one tenant.
"""
from pydantic import EmailStr, Field

from app.models.base import BaseDocument


class User(BaseDocument):
    tenant_id: str | None = None
    email: EmailStr
    password_hash: str
    full_name: str
    role: str
    status: str = "active"  # active | disabled
    extra_permissions: list[str] = Field(default_factory=list)
    last_login_at: str | None = None
