"""Tenant (School) domain model — extended for Prompt 1 school onboarding.

Every school-owned record in the platform stores `tenant_id` referring to
this collection.  A tenant is the root of the multi-tenancy hierarchy.
"""
from pydantic import EmailStr, Field

from app.models.base import BaseDocument


# --- Enumerations (kept as string literals for future-proof extensibility) ---
BOARDS = ["cbse", "cisce", "state_board", "ib", "cambridge", "other"]
SCHOOL_TYPES = ["pre_primary", "primary", "secondary", "senior_secondary", "k12"]
SCHOOL_STATUSES = ["active", "trial", "suspended", "archived"]
PLANS = ["trial", "starter", "standard", "premium", "enterprise"]


# --- Module entitlements (Step 6 of wizard) ---
DEFAULT_MODULES = {
    "crm": True,
    "attendance": True,
    "fees": True,
    "payroll": True,
    "examinations": True,
    "curriculum": True,
    "transport": False,      # future
    "library": False,        # future
    "communication": True,
    "ai_assistance": False,
}


# --- Branding defaults (Step 5) ---
DEFAULT_BRANDING = {
    "logo_url": None,
    "favicon_url": None,
    "primary_color": "#002FA7",
    "secondary_color": "#0A0A0C",
    "accent_color": "#FFCC00",
    "theme_mode": "light",              # light | dark | system
    "typography": "cabinet_grotesk",    # cabinet_grotesk | inter | plex | serif
    "dashboard_style": "modern",        # modern | classic | dense
}


# --- Contact block (Step 2) ---
DEFAULT_CONTACT = {
    "address_line": None,
    "city": None,
    "district": None,
    "state": None,
    "pin": None,
    "phone": None,
    "email": None,
    "website": None,
}


# --- Academic configuration (Step 3) ---
DEFAULT_ACADEMIC = {
    "academic_year_name": None,
    "start_date": None,
    "end_date": None,
    "classes_offered": [],
    "sections": [],
    "medium": "english",
    "working_days": ["mon", "tue", "wed", "thu", "fri"],
    "school_week": 5,
}


class Tenant(BaseDocument):
    # Step 1 — Institution
    name: str
    slug: str
    short_name: str | None = None
    school_code: str | None = None
    board: str = "other"
    school_type: str = "k12"

    # Contact — legacy Prompt 0 fields preserved
    contact_email: EmailStr
    contact_phone: str | None = None
    address: str | None = None
    country: str | None = None
    timezone: str = "UTC"

    # Extended blocks (Prompt 1)
    contact: dict = Field(default_factory=lambda: dict(DEFAULT_CONTACT))
    academic: dict = Field(default_factory=lambda: dict(DEFAULT_ACADEMIC))
    branding: dict = Field(default_factory=lambda: dict(DEFAULT_BRANDING))
    modules: dict = Field(default_factory=lambda: dict(DEFAULT_MODULES))

    # Subscription / lifecycle
    plan: str = "trial"
    status: str = "trial"                # active | trial | suspended | archived
    trial_ends_at: str | None = None
    subscription_started_at: str | None = None

    # Free-form settings bag preserved
    settings: dict = Field(default_factory=dict)
