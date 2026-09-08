"""Request/response DTOs for the v1 API."""
from datetime import datetime, date
from typing import Any

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
    tenant_slug: str | None = None


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
    short_name: str | None = None
    school_code: str | None = None
    board: str | None = None
    school_type: str | None = None
    contact_email: EmailStr
    country: str | None = None
    plan: str
    status: str
    contact: dict = {}
    academic: dict = {}
    branding: dict = {}
    modules: dict = {}
    trial_ends_at: str | None = None
    subscription_started_at: str | None = None
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserOut
    tenant: TenantOut | None = None
    impersonation: dict | None = None


# ---------- Users ----------
class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    role: str
    tenant_id: str | None = None


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    role: str | None = None
    status: str | None = None
    extra_permissions: list[str] | None = None


# ---------- Tenants (Prompt 0 patch — still used by /school/) ----------
class UpdateTenantRequest(BaseModel):
    name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    address: str | None = None
    country: str | None = None
    timezone: str | None = None
    status: str | None = None
    plan: str | None = None
    short_name: str | None = None
    school_code: str | None = None
    board: str | None = None
    school_type: str | None = None
    contact: dict | None = None
    academic: dict | None = None
    branding: dict | None = None
    modules: dict | None = None


# ---------- Platform: School creation wizard ----------
class WizardInstitution(BaseModel):
    school_name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    short_name: str | None = None
    school_code: str | None = None
    board: str = "other"
    school_type: str = "k12"


class WizardContact(BaseModel):
    address_line: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    pin: str | None = None
    country: str | None = None
    phone: str | None = None
    email: EmailStr
    website: str | None = None


class WizardAcademic(BaseModel):
    academic_year_name: str = Field(min_length=2, max_length=40)
    start_date: str | None = None   # ISO date
    end_date: str | None = None
    classes_offered: list[str] = []
    sections: list[str] = []
    medium: str = "english"
    working_days: list[str] = ["mon", "tue", "wed", "thu", "fri"]
    school_week: int = Field(default=5, ge=1, le=7)


class WizardAdministrator(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    mobile: str | None = None
    temp_password: str | None = Field(default=None, min_length=8, max_length=128)
    send_invite: bool = True


class WizardBranding(BaseModel):
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str = "#002FA7"
    secondary_color: str = "#0A0A0C"
    accent_color: str = "#FFCC00"
    theme_mode: str = "light"
    typography: str = "cabinet_grotesk"
    dashboard_style: str = "modern"


class WizardModules(BaseModel):
    crm: bool = True
    attendance: bool = True
    fees: bool = True
    payroll: bool = True
    examinations: bool = True
    curriculum: bool = True
    transport: bool = False
    library: bool = False
    communication: bool = True
    ai_assistance: bool = False


class CreateSchoolRequest(BaseModel):
    institution: WizardInstitution
    contact: WizardContact
    academic: WizardAcademic
    administrator: WizardAdministrator
    branding: WizardBranding = WizardBranding()
    modules: WizardModules = WizardModules()
    plan: str = "trial"


class CreateSchoolResponse(BaseModel):
    tenant: TenantOut
    administrator: UserOut
    temp_password: str | None = None       # returned only if platform admin generated one


# ---------- Platform: lifecycle & subscription ----------
class TenantStatusChange(BaseModel):
    status: str = Field(pattern=r"^(active|trial|suspended|archived)$")
    reason: str | None = None


class TenantPlanChange(BaseModel):
    plan: str = Field(pattern=r"^(trial|starter|standard|premium|enterprise)$")
    reason: str | None = None


class TenantEntitlementsUpdate(BaseModel):
    modules: dict


# ---------- Platform: impersonation ----------
class ImpersonateRequest(BaseModel):
    reason: str = Field(min_length=4, max_length=280)
    target_user_id: str | None = None   # optional — defaults to school owner


# ---------- Platform: alerts ----------
class AlertOut(BaseModel):
    id: str
    tenant_id: str | None
    level: str
    title: str
    message: str
    resource: str | None = None
    resource_id: str | None = None
    acknowledged: bool
    created_at: datetime


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
    metadata: dict | None = None


# ---------- Platform stats ----------
class PlatformStats(BaseModel):
    total_schools: int
    active_schools: int
    trial_schools: int
    suspended_schools: int
    archived_schools: int
    total_students: int
    total_teachers: int
    total_users: int
    mrr: float
    audit_events_30d: int
    subscription_status: dict
    recently_onboarded: list[TenantOut]
    open_alerts: int
