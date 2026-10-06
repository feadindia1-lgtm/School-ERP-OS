"""Timetable Engine + Proxy Scheduling — Prompt 7.

Design notes
------------
- Reuses the Prompt 4 academic framework (BellSchedule, WorkingDayPolicy,
  TeacherAssignment, Classes/Sections/Subjects/Rooms).  No duplicate teacher
  identity model — teacher is identified by `teacher_user_id` (and optionally
  cross-linked to Prompt-5 `employee_id`).
- A **TimetableSlot** is one weekday-period cell inside a section's master
  timetable.  Uniqueness: (tenant, academic_year, section, weekday,
  period_no).  Conflicts (teacher/room double-book) are detected at write
  time by the route layer.
- **TimetableSectionMeta** tracks publish/lock status per section so an
  admin can draft -> publish without touching individual slot rows.
- A **Substitution** is a *per-date, per-period* override that does NOT
  mutate the master timetable.  Approving a substitution flips its
  status to "approved" and records the applied_at timestamp.
- **ProxyConfig** keeps school-wide proxy rules (cutoff, auto-run,
  subject-match preference, max daily load).
"""
from pydantic import Field

from app.models.base import BaseDocument


SUBSTITUTION_STATUS = ["recommended", "pending", "approved", "rejected", "cancelled"]
SUBSTITUTION_SOURCE = ["leave", "attendance", "manual"]
TIMETABLE_PUBLISH_STATUS = ["draft", "published", "archived"]


class TimetableSectionMeta(BaseDocument):
    """Per-section publish/lock state for the master timetable."""
    tenant_id: str
    academic_year_id: str
    class_id: str
    section_id: str
    bell_schedule_id: str                   # which bell schedule drives the periods
    status: str = "draft"                   # TIMETABLE_PUBLISH_STATUS
    published_at: str | None = None
    published_by_user_id: str | None = None
    locked: bool = False
    notes: str | None = None


class TimetableSlot(BaseDocument):
    """One cell in a weekly master timetable."""
    tenant_id: str
    academic_year_id: str
    class_id: str
    section_id: str
    bell_schedule_id: str
    weekday: str                             # mon|tue|wed|thu|fri|sat|sun
    period_no: int

    subject_id: str | None = None            # None = free period / assembly
    teacher_user_id: str | None = None       # FK -> users (role=teacher/class_teacher)
    teacher_employee_id: str | None = None   # cross-link to Prompt-5 Employee
    room_id: str | None = None               # optional (section may use its homeroom)
    label: str | None = None                 # free-text ("Assembly", "Library")
    notes: str | None = None


class Substitution(BaseDocument):
    """A single-date override for one timetable slot.

    Carries a snapshot of the original (section/period/subject/original
    teacher) so a slot edited later in the year doesn't retroactively
    rewrite history.
    """
    tenant_id: str
    date: str                                # ISO date YYYY-MM-DD
    academic_year_id: str
    weekday: str
    period_no: int
    bell_schedule_id: str

    # Original slot snapshot
    timetable_slot_id: str | None = None     # None allowed when slot was free/edited
    class_id: str
    section_id: str
    subject_id: str | None = None
    original_teacher_user_id: str | None = None

    # Substitute
    substitute_teacher_user_id: str
    substitute_employee_id: str | None = None

    # Workflow
    status: str = "recommended"              # SUBSTITUTION_STATUS
    source: str = "manual"                   # SUBSTITUTION_SOURCE
    rank_score: float | None = None
    criteria_used: list[dict] = Field(default_factory=list)   # [{code, label, delta, hit}]

    requested_by_user_id: str | None = None
    approved_by_user_id: str | None = None
    approved_at: str | None = None
    rejected_by_user_id: str | None = None
    decision_reason: str | None = None
    cancelled_at: str | None = None

    notes: str | None = None


class ProxyConfig(BaseDocument):
    """School-wide proxy / substitute rules.  One doc per tenant."""
    tenant_id: str

    # Absence detection
    cutoff_time: str = "09:30"               # HH:MM — unmarked attendance beyond this = presumed absent
    attendance_grace_minutes: int = 15       # how late is still 'present'
    use_leave_source: bool = True            # approved leave triggers absence
    use_attendance_source: bool = True       # attendance after cutoff triggers absence

    # Auto-detection
    auto_run_enabled: bool = False
    auto_run_time: str = "08:00"             # when scheduler would fire (future prompt)

    # Ranking preferences
    require_subject_match: bool = False
    prefer_same_grade: bool = True
    max_proxy_per_day_per_teacher: int = 3

    # Notifications (in-app only this prompt)
    notify_substitute: bool = True
    notify_class_teacher: bool = True
    notify_admin: bool = True

    notes: str | None = None
