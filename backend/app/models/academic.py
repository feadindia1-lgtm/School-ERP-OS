"""Academic Structure & School Calendar models — Prompt 4.

Provides the authoritative academic context (year → class → section →
subject → room → bell schedule → holidays → teacher assignment) consumed by
every downstream module (Attendance, Fees, Timetable, Exams, Curriculum).

Rules:
- Every doc is tenant-scoped.
- Historical academic years are immutable (status="archived") — mutations
  raise 409 unless the year is "current" or "planning".
- A section belongs to exactly one class within one academic year.
- Teacher assignments point at `users` collection rows with role=teacher.
"""
from pydantic import Field

from app.models.base import BaseDocument


# --- Vocabulary presets by education board ---------------------------------
# Terminology admins can override at BoardConfig level.  Kept short: labels
# only.  Term structure (Term/Semester count) also declared per board.
BOARD_PRESETS: dict[str, dict] = {
    "CBSE":     {"class_label": "Class",    "section_label": "Section", "terms": ["Term 1", "Term 2"]},
    "ICSE":     {"class_label": "Standard", "section_label": "Section", "terms": ["Term 1", "Term 2"]},
    "IB":       {"class_label": "Grade",    "section_label": "House",   "terms": ["Semester 1", "Semester 2"]},
    "IGCSE":    {"class_label": "Year",     "section_label": "Form",    "terms": ["Semester 1", "Semester 2"]},
    "STATE":    {"class_label": "Class",    "section_label": "Section", "terms": ["Quarter 1", "Quarter 2", "Quarter 3", "Quarter 4"]},
    "CUSTOM":   {"class_label": "Class",    "section_label": "Section", "terms": ["Term 1", "Term 2"]},
}

ACADEMIC_YEAR_STATUSES = ["planning", "current", "archived"]
SUBJECT_TYPES = ["theory", "practical", "lab", "co_scholastic", "language", "elective"]
ROOM_TYPES = ["classroom", "lab", "auditorium", "library", "sports", "computer_lab", "other"]
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class AcademicYear(BaseDocument):
    tenant_id: str
    name: str                      # e.g. "2025-26"
    start_date: str                # ISO date
    end_date: str                  # ISO date
    is_current: bool = False
    status: str = "planning"       # planning | current | archived
    board_preset: str = "CBSE"     # snapshot of the board preset at creation
    term_names: list[str] = Field(default_factory=list)
    notes: str | None = None


class BoardConfig(BaseDocument):
    """Per-tenant terminology and defaults.  Seeded from the tenant's `board`
    field on first read and then user-editable."""
    tenant_id: str
    board: str = "CBSE"
    class_label: str = "Class"
    section_label: str = "Section"
    terms: list[str] = Field(default_factory=list)
    marking_style: str = "percentage"     # percentage | gpa | grades (used later)


class AcademicClass(BaseDocument):
    """Grade/Standard within an academic year (e.g. Class 5, XII-Science)."""
    tenant_id: str
    academic_year_id: str
    name: str                      # display name — "Class 5", "Nursery"
    code: str                      # short slug — "5", "NUR", "XII-SCI"
    stream: str | None = None      # optional — "Science" / "Commerce" / "Arts"
    order: int = 0                 # sort key
    description: str | None = None


class AcademicSection(BaseDocument):
    """Division within a class (e.g. 5-A, 5-B)."""
    tenant_id: str
    academic_year_id: str
    class_id: str
    name: str                      # "A", "B", "Rose"
    capacity: int | None = None
    class_teacher_user_id: str | None = None   # FK -> users._id (role=teacher)
    room_id: str | None = None                 # default homeroom
    notes: str | None = None


class Subject(BaseDocument):
    tenant_id: str
    name: str                      # "Mathematics"
    code: str                      # "MATH"
    subject_type: str = "theory"   # see SUBJECT_TYPES
    is_optional: bool = False
    description: str | None = None


class SubjectGroup(BaseDocument):
    """Bundle of subjects offered to a specific class (e.g. Grade 10 Core)."""
    tenant_id: str
    academic_year_id: str
    class_id: str
    name: str
    subject_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class Room(BaseDocument):
    tenant_id: str
    name: str                      # "Room 101"
    code: str                      # "R101"
    room_type: str = "classroom"
    capacity: int | None = None
    floor: str | None = None
    building: str | None = None
    description: str | None = None


class BellSchedule(BaseDocument):
    """Named schedule (e.g. Weekday, Half-day) with an ordered list of periods.

    A period is stored inline as a dict:
      { period_no, label, start_time, end_time, is_break, duration_minutes }
    """
    tenant_id: str
    academic_year_id: str
    name: str
    is_default: bool = False
    periods: list[dict] = Field(default_factory=list)
    notes: str | None = None


class WorkingDayPolicy(BaseDocument):
    """One row per tenant per academic year defining working days and weekly-off."""
    tenant_id: str
    academic_year_id: str
    working_days: list[str] = Field(default_factory=lambda: ["mon", "tue", "wed", "thu", "fri"])
    half_days: list[str] = Field(default_factory=list)         # subset of working_days
    weekly_off: list[str] = Field(default_factory=lambda: ["sat", "sun"])
    notes: str | None = None


class Holiday(BaseDocument):
    tenant_id: str
    academic_year_id: str
    name: str
    start_date: str                # ISO date
    end_date: str                  # ISO date (== start_date for single-day)
    category: str = "public"       # public | school | optional | exam
    is_recurring: bool = False
    notes: str | None = None


class TeacherAssignment(BaseDocument):
    """M:N join — teacher × class × section × subject × academic_year.

    Used later by Attendance (class-teacher), Timetable (subject teacher),
    Exams (grading rights) and Curriculum (lesson plan authorship).
    """
    tenant_id: str
    academic_year_id: str
    teacher_user_id: str            # FK -> users._id (must have role=teacher/class_teacher)
    employee_id: str | None = None  # FK -> employees._id (Prompt 5); kept in sync
    class_id: str
    section_id: str | None = None   # null = whole-class role
    subject_id: str | None = None   # null = class-teacher role
    is_class_teacher: bool = False
    weekly_periods: int | None = None
    notes: str | None = None
