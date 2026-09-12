"""Staff Master + Leave Foundation — Prompt 5.

Employee is a separate collection. A login `users` row may optionally link
via `user_id`. `TeacherAssignment` (Prompt 4) is extended with an optional
`employee_id`; the two identifiers are kept in sync at write time.
"""
from pydantic import Field

from app.models.base import BaseDocument


EMPLOYMENT_TYPES = ["full_time", "part_time", "contract", "visiting", "intern", "consultant"]
EMPLOYMENT_STATUSES = [
    "active", "probation", "on_leave", "suspended", "resigned",
    "terminated", "retired", "notice_period",
]
LEAVE_APPLICABLE_TO = ["all", "teaching", "non_teaching", "male", "female", "specific"]
LEAVE_ACCRUAL_FREQ = ["yearly", "monthly", "quarterly", "one_time"]
LEAVE_STATUS = ["pending", "approved_l1", "approved", "rejected", "cancelled", "withdrawn"]
LEAVE_ADJUST_REASONS = ["carry_forward", "encashment", "correction", "grant", "revoke", "other"]


class Department(BaseDocument):
    tenant_id: str
    name: str
    code: str
    head_user_id: str | None = None
    description: str | None = None


class Designation(BaseDocument):
    tenant_id: str
    title: str
    code: str
    department_id: str | None = None    # optional link
    is_teaching: bool = False
    grade: str | None = None
    description: str | None = None


class Employee(BaseDocument):
    """Canonical staff record — one per person employed by the school."""
    tenant_id: str
    employee_code: str                   # EMP-YYYY-NNNN (auto or admin override)
    user_id: str | None = None           # FK -> users._id when they have a login

    # Identity
    first_name: str
    middle_name: str | None = None
    last_name: str | None = None
    preferred_name: str | None = None
    gender: str | None = None
    date_of_birth: str | None = None
    blood_group: str | None = None
    nationality: str | None = None
    photo_url: str | None = None

    # Contact
    mobile_primary: str | None = None
    mobile_secondary: str | None = None
    email_personal: str | None = None
    address: dict | None = None

    # Employment
    department_id: str | None = None
    designation_id: str | None = None
    employment_type: str = "full_time"
    joining_date: str | None = None
    probation_end_date: str | None = None
    confirmation_date: str | None = None
    exit_date: str | None = None
    exit_reason: str | None = None
    reporting_to_employee_id: str | None = None

    # Teacher-specific hints (populated when qualifications exist)
    is_teaching_staff: bool = False
    subjects_qualified: list[str] = Field(default_factory=list)   # subject IDs
    classes_eligible: list[str] = Field(default_factory=list)     # class IDs

    # Attendance hooks (Prompt 6 will consume)
    biometric_id: str | None = None
    attendance_number: str | None = None
    default_working_days: list[str] = Field(default_factory=list)  # override tenant policy

    # Status
    status: str = "active"
    status_reason: str | None = None
    status_effective_date: str | None = None

    # Emergency + KYC
    emergency_contact: dict | None = None
    kyc: dict = Field(default_factory=dict)   # PAN, Aadhaar, bank etc — free-form
    document_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class EmployeeDocument(BaseDocument):
    tenant_id: str
    employee_id: str
    doc_type: str                          # "aadhaar" / "pan" / "resume" / …
    filename: str
    storage_key: str                       # opaque handle from storage service
    size_bytes: int | None = None
    mime_type: str | None = None
    status: str = "uploaded"               # uploaded | verified | rejected
    uploaded_by_user_id: str | None = None
    verified_by_user_id: str | None = None
    verified_at: str | None = None
    notes: str | None = None


class EmployeeQualification(BaseDocument):
    """A teacher's subject/class-eligibility grid, plus academic degrees.

    Kept separate from `TeacherAssignment` (Prompt 4) — assignments describe
    a *current-year work allocation*, whereas qualification describes what a
    teacher is *allowed to teach*.
    """
    tenant_id: str
    employee_id: str
    kind: str = "subject"                  # subject | degree | certification
    subject_id: str | None = None
    class_id: str | None = None
    degree_name: str | None = None
    institution: str | None = None
    year_of_completion: str | None = None
    grade: str | None = None
    notes: str | None = None


# --- Leave -----------------------------------------------------------------
class LeaveType(BaseDocument):
    tenant_id: str
    name: str                              # "Casual Leave"
    code: str                              # "CL"
    is_paid: bool = True
    max_per_year: float | None = None
    accrual_frequency: str = "yearly"      # yearly | monthly | quarterly | one_time
    carry_forward: bool = False
    carry_forward_max: float | None = None
    applicable_to: str = "all"
    approval_steps: int = 1                # 1 = single-step (HR); 2 = manager+HR
    requires_document: bool = False
    is_active: bool = True
    description: str | None = None
    color: str | None = None               # UI hint


class LeaveBalance(BaseDocument):
    """One row per (employee, leave_type, year)."""
    tenant_id: str
    employee_id: str
    leave_type_id: str
    year: str                              # academic-year name OR calendar year — free-form
    allocated: float = 0
    used: float = 0
    adjustment: float = 0
    balance: float = 0                     # allocated + adjustment - used
    last_updated_at: str | None = None


class LeaveApplication(BaseDocument):
    tenant_id: str
    employee_id: str
    leave_type_id: str
    start_date: str                        # ISO date
    end_date: str                          # ISO date
    days: float                            # calendar days (or half-day)
    is_half_day: bool = False
    reason: str
    supporting_document_id: str | None = None
    status: str = "pending"                # LEAVE_STATUS
    approval_steps_required: int = 1
    approver_l1_user_id: str | None = None
    approver_l2_user_id: str | None = None
    approved_by_user_id: str | None = None
    rejected_by_user_id: str | None = None
    decision_reason: str | None = None
    decision_at: str | None = None
    applied_by_user_id: str | None = None
    year: str | None = None                # denormalised for balance rollup


class LeaveAdjustment(BaseDocument):
    """Manual credit/debit of leave balance (audit trail)."""
    tenant_id: str
    employee_id: str
    leave_type_id: str
    year: str
    amount: float                          # positive = credit, negative = debit
    reason: str = "correction"
    notes: str | None = None
    actor_user_id: str | None = None
