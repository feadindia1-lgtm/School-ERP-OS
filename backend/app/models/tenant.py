"""Tenant (School) domain model.

Every school-owned record in the platform stores `tenant_id` referring to
this collection.  A tenant is the root of the multi-tenancy hierarchy.
"""
from pydantic import EmailStr, Field

from app.models.base import BaseDocument


class Tenant(BaseDocument):
    name: str
    slug: str  # unique url-safe identifier
    contact_email: EmailStr
    contact_phone: str | None = None
    address: str | None = None
    country: str | None = None
    timezone: str = "UTC"
    plan: str = "trial"  # trial | standard | premium
    status: str = "active"  # active | suspended | cancelled
    settings: dict = Field(default_factory=dict)
