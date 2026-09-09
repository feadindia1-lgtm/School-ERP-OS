"""Canonical Student & Family models.

⚠️  Student Master is the SINGLE authoritative student identity for the
entire School OS.  Do NOT create a parallel student collection.

The Prompt-2 `StudentStub` and `GuardianStub` have been evolved *in place*
into the production `Student` and `Guardian` models below — same
collections (`students`, `guardians`) and preserved `_id`s.
"""
from pydantic import Field

from app.models.base import BaseDocument


LIFECYCLE_STATES = [
    "PROSPECT", "ACTIVE", "INACTIVE", "ON_LEAVE",
    "TRANSFERRED", "WITHDRAWN", "GRADUATED", "ALUMNI",
]

RELATIONSHIP_TYPES = [
    "father", "mother", "guardian", "legal_guardian", "step_parent",
    "grandparent", "sibling", "other",
]


class Student(BaseDocument):
    """Canonical Student Master record."""
    tenant_id: str
    admission_number: str
    roll_number: str | None = None
    student_code: str | None = None

    first_name: str
    middle_name: str | None = None
    last_name: str | None = None
    preferred_name: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    blood_group: str | None = None
    nationality: str | None = None
    mother_tongue: str | None = None
    category: str | None = None
    profile_photo_url: str | None = None

    # Current academic snapshot (history in student_enrollments)
    academic_year: str | None = None
    class_name: str | None = None
    section: str | None = None
    house: str | None = None

    # Address
    residential_address: dict | None = None
    permanent_address: dict | None = None

    # Provenance
    application_id: str | None = None
    lead_id: str | None = None
    family_id: str | None = None
    admission_date: str | None = None

    # Lifecycle
    status: str = "ACTIVE"
    status_reason: str | None = None
    status_effective_date: str | None = None

    document_ids: list[str] = Field(default_factory=list)


class Guardian(BaseDocument):
    """Canonical Guardian Master.  Guardians can be linked to multiple students."""
    tenant_id: str
    first_name: str
    middle_name: str | None = None
    last_name: str | None = None
    relationship_type: str = "guardian"
    mobile_primary: str
    mobile_secondary: str | None = None
    email: str | None = None
    occupation: str | None = None
    employer: str | None = None
    address: dict | None = None
    preferred_language: str | None = None
    communication_preferences: dict = Field(default_factory=dict)
    emergency_contact_flag: bool = False
    family_id: str | None = None
    status: str = "active"


class StudentGuardian(BaseDocument):
    """Many-to-many relationship linking Student ↔ Guardian."""
    tenant_id: str
    student_id: str
    guardian_id: str
    relationship_type: str = "guardian"
    is_primary: bool = False
    is_emergency_contact: bool = False
    has_pickup_authorization: bool = False
    has_fee_responsibility: bool = False
    has_academic_access: bool = True
    communication_priority: int = 1
    start_date: str | None = None
    end_date: str | None = None
    notes: str | None = None


class Family(BaseDocument):
    """Optional grouping of students + guardians that share a household."""
    tenant_id: str
    family_name: str
    primary_contact_guardian_id: str | None = None
    address: dict | None = None
    communication_preferences: dict = Field(default_factory=dict)
    notes: str | None = None


class StudentEnrollment(BaseDocument):
    """Historical academic placement — one row per academic year per student."""
    tenant_id: str
    student_id: str
    academic_year: str
    class_name: str
    section: str | None = None
    roll_number: str | None = None
    house: str | None = None
    enrollment_status: str = "active"    # active | promoted | detained | withdrawn
    start_date: str | None = None
    end_date: str | None = None
    promotion_status: str | None = None
    remarks: str | None = None
