"""Admission-domain models: applications, documents, conversions, settings."""
from pydantic import Field

from app.models.base import BaseDocument


# --- Application state machine ---------------------------------------------
APP_DRAFT = "DRAFT"
APP_SUBMITTED = "SUBMITTED"
APP_UNDER_REVIEW = "UNDER_REVIEW"
APP_DOCUMENTS_PENDING = "DOCUMENTS_PENDING"
APP_APPROVED = "APPROVED"
APP_REJECTED = "REJECTED"
APP_WITHDRAWN = "WITHDRAWN"
APP_CONVERTED = "CONVERTED"

APP_STATES = [APP_DRAFT, APP_SUBMITTED, APP_UNDER_REVIEW, APP_DOCUMENTS_PENDING,
              APP_APPROVED, APP_REJECTED, APP_WITHDRAWN, APP_CONVERTED]

# Transition matrix — allowed next states for each state
APP_TRANSITIONS = {
    APP_DRAFT: {APP_SUBMITTED, APP_WITHDRAWN},
    APP_SUBMITTED: {APP_UNDER_REVIEW, APP_WITHDRAWN, APP_DOCUMENTS_PENDING},
    APP_UNDER_REVIEW: {APP_APPROVED, APP_REJECTED, APP_DOCUMENTS_PENDING, APP_WITHDRAWN},
    APP_DOCUMENTS_PENDING: {APP_UNDER_REVIEW, APP_WITHDRAWN, APP_REJECTED},
    APP_APPROVED: {APP_CONVERTED, APP_WITHDRAWN},
    APP_REJECTED: set(),
    APP_WITHDRAWN: set(),
    APP_CONVERTED: set(),
}


class AdmissionApplication(BaseDocument):
    tenant_id: str
    application_number: str
    lead_id: str | None = None
    academic_year: str
    class_requested: str

    # Student
    student_first_name: str
    student_last_name: str
    student_dob: str | None = None
    student_gender: str | None = None
    previous_school: str | None = None

    # Parent
    parent_name: str
    parent_relationship: str = "guardian"
    parent_mobile: str
    parent_email: str | None = None

    status: str = APP_DRAFT
    submitted_at: str | None = None
    assigned_reviewer: str | None = None
    review_notes: str | None = None
    decision_at: str | None = None
    decided_by: str | None = None
    rejection_reason: str | None = None
    correction_requested: str | None = None

    student_id: str | None = None
    converted_at: str | None = None


# --- Documents -------------------------------------------------------------
DOC_PENDING = "PENDING"
DOC_VERIFIED = "VERIFIED"
DOC_REJECTED = "REJECTED"
DOC_NOT_REQUIRED = "NOT_REQUIRED"

DOC_STATUSES = [DOC_PENDING, DOC_VERIFIED, DOC_REJECTED, DOC_NOT_REQUIRED]


class AdmissionDocumentType(BaseDocument):
    """Tenant-configurable document type."""
    tenant_id: str
    code: str                          # e.g. "birth_certificate"
    label: str                         # human-friendly
    requirement: str = "required"      # required | optional | conditional
    condition_note: str | None = None
    active: bool = True
    order: int = 0


DEFAULT_DOC_TYPES = [
    {"code": "birth_certificate", "label": "Birth Certificate", "requirement": "required", "order": 1},
    {"code": "previous_report_card", "label": "Previous Report Card", "requirement": "required", "order": 2},
    {"code": "transfer_certificate", "label": "Transfer Certificate", "requirement": "conditional", "condition_note": "If joining from another school", "order": 3},
    {"code": "identity_document", "label": "Identity Document", "requirement": "conditional", "condition_note": "Any govt. ID (Aadhaar/Passport/etc.)", "order": 4},
    {"code": "passport_photo", "label": "Passport Photo", "requirement": "required", "order": 5},
    {"code": "address_proof", "label": "Address Proof", "requirement": "optional", "order": 6},
]


class AdmissionDocument(BaseDocument):
    tenant_id: str
    application_id: str
    type_code: str
    type_label: str
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    storage_key: str | None = None       # provider-native key
    status: str = DOC_PENDING
    uploaded_by: str | None = None
    uploaded_at: str | None = None
    verified_by: str | None = None
    verified_at: str | None = None
    rejection_reason: str | None = None


# --- Conversion ------------------------------------------------------------
class AdmissionConversion(BaseDocument):
    tenant_id: str
    application_id: str
    lead_id: str | None = None
    student_id: str                    # placeholder — Student Master lands in a later prompt
    student_number: str | None = None
    guardian_ids: list[str] = Field(default_factory=list)
    converted_by: str
    metadata: dict = Field(default_factory=dict)


# --- Placeholder Student / Guardian removed in Prompt 3 ---------------------
# The canonical Student and Guardian models now live in `app.models.student`.
# The Prompt-2 `StudentStub` and `GuardianStub` classes were EVOLVED IN PLACE
# into `Student` and `Guardian`; the `students` and `guardians` collections
# are preserved along with their `_id`s.


# --- CRM / Admission settings (per tenant) ---------------------------------
class AdmissionSettings(BaseDocument):
    tenant_id: str
    pipeline_stages: list[dict] = Field(default_factory=list)     # {code, label, order, color, is_won, is_lost}
    sources: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    doc_types: list[dict] = Field(default_factory=list)           # {code, label, requirement, order}
    require_docs_for_approval: bool = True
