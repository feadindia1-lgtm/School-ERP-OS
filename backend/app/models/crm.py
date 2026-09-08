"""CRM domain models — leads, activities, follow-ups, campus visits.

All records carry `tenant_id` and are enforced tenant-scoped by the routes.
"""
from pydantic import Field

from app.models.base import BaseDocument


# --- Pipeline stages ------------------------------------------------------
STAGE_NEW_INQUIRY = "NEW_INQUIRY"
STAGE_CONTACTED = "CONTACTED"
STAGE_VISIT_SCHEDULED = "VISIT_SCHEDULED"
STAGE_FORM_FILLED = "FORM_FILLED"
STAGE_UNDER_REVIEW = "UNDER_REVIEW"
STAGE_APPROVED = "APPROVED"
STAGE_FEE_PENDING = "FEE_PENDING"
STAGE_ADMITTED = "ADMITTED"
STAGE_LOST = "LOST"

DEFAULT_PIPELINE = [
    {"code": STAGE_NEW_INQUIRY, "label": "New Inquiry", "order": 1, "color": "#002FA7", "is_won": False, "is_lost": False},
    {"code": STAGE_CONTACTED, "label": "Contacted", "order": 2, "color": "#3B82F6", "is_won": False, "is_lost": False},
    {"code": STAGE_VISIT_SCHEDULED, "label": "Campus Visit Scheduled", "order": 3, "color": "#8B5CF6", "is_won": False, "is_lost": False},
    {"code": STAGE_FORM_FILLED, "label": "Form Filled", "order": 4, "color": "#EC4899", "is_won": False, "is_lost": False},
    {"code": STAGE_UNDER_REVIEW, "label": "Under Review", "order": 5, "color": "#F59E0B", "is_won": False, "is_lost": False},
    {"code": STAGE_APPROVED, "label": "Approved", "order": 6, "color": "#10B981", "is_won": False, "is_lost": False},
    {"code": STAGE_FEE_PENDING, "label": "Fee Pending", "order": 7, "color": "#FFCC00", "is_won": False, "is_lost": False},
    {"code": STAGE_ADMITTED, "label": "Admitted", "order": 8, "color": "#059669", "is_won": True, "is_lost": False},
    {"code": STAGE_LOST, "label": "Lost / Rejected", "order": 99, "color": "#FF3B30", "is_won": False, "is_lost": True},
]

DEFAULT_SOURCES = [
    "website", "walk_in", "phone", "whatsapp", "referral",
    "existing_parent", "advertisement", "social_media", "event", "other",
]

PRIORITIES = ["low", "medium", "high", "urgent"]


# --- Lead / Prospect ------------------------------------------------------
class CrmLead(BaseDocument):
    tenant_id: str
    inquiry_number: str

    # Student / prospect
    student_first_name: str
    student_last_name: str
    student_dob: str | None = None      # ISO date
    student_gender: str | None = None
    class_seeking: str | None = None
    academic_year: str | None = None
    previous_school: str | None = None

    # Parent / guardian
    parent_name: str
    parent_relationship: str = "guardian"
    parent_mobile: str
    parent_email: str | None = None
    alt_contact: str | None = None

    # Inquiry meta
    source: str = "other"
    preferred_contact: str = "phone"
    assigned_to: str | None = None       # user_id
    priority: str = "medium"
    notes: str | None = None
    inquiry_date: str | None = None      # ISO datetime

    stage: str = STAGE_NEW_INQUIRY
    last_activity_at: str | None = None
    next_followup_at: str | None = None

    # Backrefs
    application_id: str | None = None
    student_id: str | None = None
    converted_at: str | None = None

    lost_reason: str | None = None
    tags: list[str] = Field(default_factory=list)


ACTIVITY_TYPES = [
    "phone_call", "whatsapp", "sms", "email", "campus_visit",
    "meeting", "note", "task", "application_update", "other",
]


class CrmActivity(BaseDocument):
    tenant_id: str
    lead_id: str
    activity_type: str
    subject: str | None = None
    outcome: str | None = None
    notes: str | None = None
    activity_at: str | None = None          # ISO datetime
    user_id: str | None = None              # actor
    next_action: str | None = None
    next_followup_at: str | None = None
    is_system: bool = False                 # true for auto-generated timeline events


FOLLOWUP_STATUSES = ["pending", "completed", "cancelled"]


class Followup(BaseDocument):
    tenant_id: str
    lead_id: str
    due_at: str                              # ISO datetime
    title: str
    channel: str = "phone_call"              # phone_call | whatsapp | sms | email | meeting
    notes: str | None = None
    assigned_to: str | None = None
    status: str = "pending"                  # pending | completed | cancelled
    completed_at: str | None = None
    completed_by: str | None = None
    completion_notes: str | None = None


VISIT_STATUSES = ["scheduled", "confirmed", "completed", "cancelled", "no_show"]


class CampusVisit(BaseDocument):
    tenant_id: str
    lead_id: str
    scheduled_date: str                      # ISO date
    start_time: str                          # HH:MM
    end_time: str
    expected_visitors: int = 1
    assigned_staff_id: str | None = None
    purpose: str | None = None
    status: str = "scheduled"
    notes: str | None = None
