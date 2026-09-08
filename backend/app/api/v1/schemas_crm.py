"""CRM & admission DTOs."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---------- Lead ----------
class CreateLeadRequest(BaseModel):
    student_first_name: str = Field(min_length=1, max_length=80)
    student_last_name: str = Field(min_length=1, max_length=80)
    student_dob: str | None = None
    student_gender: str | None = None
    class_seeking: str | None = None
    academic_year: str | None = None
    previous_school: str | None = None

    parent_name: str = Field(min_length=1, max_length=120)
    parent_relationship: str = "guardian"
    parent_mobile: str = Field(min_length=4, max_length=32)
    parent_email: EmailStr | None = None
    alt_contact: str | None = None

    source: str = "other"
    preferred_contact: str = "phone"
    assigned_to: str | None = None
    priority: str = "medium"
    notes: str | None = None
    inquiry_date: str | None = None

    force: bool = False   # override duplicate detection


class UpdateLeadRequest(BaseModel):
    student_first_name: str | None = None
    student_last_name: str | None = None
    student_dob: str | None = None
    student_gender: str | None = None
    class_seeking: str | None = None
    academic_year: str | None = None
    previous_school: str | None = None
    parent_name: str | None = None
    parent_relationship: str | None = None
    parent_mobile: str | None = None
    parent_email: EmailStr | None = None
    alt_contact: str | None = None
    source: str | None = None
    preferred_contact: str | None = None
    assigned_to: str | None = None
    priority: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    lost_reason: str | None = None


class StageMoveRequest(BaseModel):
    stage: str
    reason: str | None = None


class AssignRequest(BaseModel):
    assigned_to: str


class LeadOut(BaseModel):
    id: str
    tenant_id: str
    inquiry_number: str
    student_first_name: str
    student_last_name: str
    student_dob: str | None = None
    student_gender: str | None = None
    class_seeking: str | None = None
    academic_year: str | None = None
    previous_school: str | None = None
    parent_name: str
    parent_relationship: str
    parent_mobile: str
    parent_email: str | None = None
    alt_contact: str | None = None
    source: str
    preferred_contact: str
    assigned_to: str | None = None
    priority: str
    notes: str | None = None
    inquiry_date: str | None = None
    stage: str
    last_activity_at: str | None = None
    next_followup_at: str | None = None
    application_id: str | None = None
    student_id: str | None = None
    converted_at: str | None = None
    lost_reason: str | None = None
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime


class PagedLeads(BaseModel):
    items: list[LeadOut]
    total: int
    page: int
    page_size: int


class DuplicateCheckResult(BaseModel):
    duplicates: list[LeadOut]


# ---------- Activity ----------
class CreateActivityRequest(BaseModel):
    activity_type: str
    subject: str | None = None
    outcome: str | None = None
    notes: str | None = None
    activity_at: str | None = None
    next_action: str | None = None
    next_followup_at: str | None = None


class ActivityOut(BaseModel):
    id: str
    lead_id: str
    activity_type: str
    subject: str | None = None
    outcome: str | None = None
    notes: str | None = None
    activity_at: str | None = None
    user_id: str | None = None
    next_action: str | None = None
    next_followup_at: str | None = None
    is_system: bool
    created_at: datetime


# ---------- Followup ----------
class CreateFollowupRequest(BaseModel):
    due_at: str
    title: str = Field(min_length=1, max_length=200)
    channel: str = "phone_call"
    notes: str | None = None
    assigned_to: str | None = None


class UpdateFollowupRequest(BaseModel):
    due_at: str | None = None
    title: str | None = None
    channel: str | None = None
    notes: str | None = None
    assigned_to: str | None = None
    status: str | None = None
    completion_notes: str | None = None


class FollowupOut(BaseModel):
    id: str
    lead_id: str
    due_at: str
    title: str
    channel: str
    notes: str | None = None
    assigned_to: str | None = None
    status: str
    completed_at: str | None = None
    completed_by: str | None = None
    completion_notes: str | None = None
    created_at: datetime


# ---------- Campus visit ----------
class CreateVisitRequest(BaseModel):
    lead_id: str
    scheduled_date: str
    start_time: str
    end_time: str
    expected_visitors: int = 1
    assigned_staff_id: str | None = None
    purpose: str | None = None
    notes: str | None = None


class UpdateVisitRequest(BaseModel):
    scheduled_date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    expected_visitors: int | None = None
    assigned_staff_id: str | None = None
    purpose: str | None = None
    notes: str | None = None
    status: str | None = None


class VisitOut(BaseModel):
    id: str
    lead_id: str
    scheduled_date: str
    start_time: str
    end_time: str
    expected_visitors: int
    assigned_staff_id: str | None = None
    purpose: str | None = None
    status: str
    notes: str | None = None
    created_at: datetime


# ---------- Application ----------
class CreateApplicationRequest(BaseModel):
    lead_id: str | None = None
    academic_year: str = Field(min_length=1, max_length=40)
    class_requested: str = Field(min_length=1, max_length=40)
    student_first_name: str
    student_last_name: str
    student_dob: str | None = None
    student_gender: str | None = None
    previous_school: str | None = None
    parent_name: str
    parent_relationship: str = "guardian"
    parent_mobile: str
    parent_email: EmailStr | None = None


class UpdateApplicationRequest(BaseModel):
    academic_year: str | None = None
    class_requested: str | None = None
    student_first_name: str | None = None
    student_last_name: str | None = None
    student_dob: str | None = None
    student_gender: str | None = None
    previous_school: str | None = None
    parent_name: str | None = None
    parent_relationship: str | None = None
    parent_mobile: str | None = None
    parent_email: EmailStr | None = None
    assigned_reviewer: str | None = None
    review_notes: str | None = None


class ApplicationStatusChange(BaseModel):
    status: str
    reason: str | None = None
    review_notes: str | None = None


class ApplicationOut(BaseModel):
    id: str
    tenant_id: str
    application_number: str
    lead_id: str | None = None
    academic_year: str
    class_requested: str
    student_first_name: str
    student_last_name: str
    student_dob: str | None = None
    student_gender: str | None = None
    previous_school: str | None = None
    parent_name: str
    parent_relationship: str
    parent_mobile: str
    parent_email: str | None = None
    status: str
    submitted_at: str | None = None
    assigned_reviewer: str | None = None
    review_notes: str | None = None
    decision_at: str | None = None
    decided_by: str | None = None
    rejection_reason: str | None = None
    correction_requested: str | None = None
    student_id: str | None = None
    converted_at: str | None = None
    created_at: datetime
    updated_at: datetime


class PagedApplications(BaseModel):
    items: list[ApplicationOut]
    total: int
    page: int
    page_size: int


# ---------- Documents ----------
class DocumentOut(BaseModel):
    id: str
    application_id: str
    type_code: str
    type_label: str
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    status: str
    uploaded_by: str | None = None
    uploaded_at: str | None = None
    verified_by: str | None = None
    verified_at: str | None = None
    rejection_reason: str | None = None
    created_at: datetime


class DocumentVerifyRequest(BaseModel):
    status: str  # VERIFIED | REJECTED
    rejection_reason: str | None = None


# ---------- Conversion ----------
class ConvertRequest(BaseModel):
    override_docs: bool = False


class ConversionResult(BaseModel):
    application_id: str
    student_id: str
    student_number: str | None = None
    conversion_id: str
    already_converted: bool


# ---------- Settings ----------
class AdmissionSettingsOut(BaseModel):
    pipeline_stages: list[dict]
    sources: list[str]
    priorities: list[str]
    doc_types: list[dict]
    require_docs_for_approval: bool


class UpdateSettingsRequest(BaseModel):
    pipeline_stages: list[dict] | None = None
    sources: list[str] | None = None
    priorities: list[str] | None = None
    doc_types: list[dict] | None = None
    require_docs_for_approval: bool | None = None


# ---------- Dashboard ----------
class DashboardResponse(BaseModel):
    total_inquiries: int
    new_inquiries_7d: int
    followups_due_today: int
    overdue_followups: int
    upcoming_visits_7d: int
    applications_in_progress: int
    applications_pending_review: int
    applications_approved: int
    admissions_confirmed: int
    lost_or_rejected: int
    conversion_rate: float
    stage_counts: dict
    source_counts: dict
    class_counts: dict
