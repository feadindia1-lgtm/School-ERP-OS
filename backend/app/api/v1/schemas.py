"""Request/response DTOs for the v1 API."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------- Auth ----------
class RegisterSchoolRequest(BaseModel):
    school_name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    contact_email: EmailStr
    country: str | None = None
    owner_full_name: str = Field(min_length=2, max_length=120)
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str | None = None  # optional disambiguator if email exists in multiple tenants


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: str
    role: str
    tenant_id: str | None
    status: str
    permissions: list[str] = []


class TenantOut(BaseModel):
    id: str
    name: str
    slug: str
    contact_email: EmailStr
    country: str | None = None
    plan: str
    status: str
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserOut
    tenant: TenantOut | None = None


# ---------- Users ----------
class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    role: str
    tenant_id: str | None = None  # required only for platform admin creating cross-tenant


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    role: str | None = None
    status: str | None = None
    extra_permissions: list[str] | None = None


# ---------- Tenants ----------
class UpdateTenantRequest(BaseModel):
    name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    address: str | None = None
    country: str | None = None
    timezone: str | None = None
    status: str | None = None
    plan: str | None = None


# ---------- Audit ----------
class AuditLogOut(BaseModel):
    id: str
    tenant_id: str | None
    actor_id: str | None
    actor_email: str | None
    actor_role: str | None
    action: str
    resource: str
    resource_id: str | None
    ip: str | None
    created_at: datetime
