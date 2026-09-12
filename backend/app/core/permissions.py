"""RBAC — roles, permissions and role→permission mapping.

Permissions are granular strings (`resource.action`).  Authorization checks
against permission strings, never role names, so new roles can be added
without touching endpoint code.
"""

# --- Roles -----------------------------------------------------------------
ROLE_PLATFORM_SUPERADMIN = "platform_superadmin"
ROLE_SCHOOL_OWNER = "school_owner"
ROLE_PRINCIPAL = "principal"
ROLE_SCHOOL_ADMIN = "school_admin"
ROLE_ADMISSION_OFFICER = "admission_officer"
ROLE_ACCOUNTANT = "accountant"
ROLE_HR_OFFICER = "hr_officer"
ROLE_TEACHER = "teacher"
ROLE_CLASS_TEACHER = "class_teacher"
ROLE_STUDENT = "student"
ROLE_PARENT = "parent"

ALL_ROLES = [
    ROLE_PLATFORM_SUPERADMIN,
    ROLE_SCHOOL_OWNER,
    ROLE_PRINCIPAL,
    ROLE_SCHOOL_ADMIN,
    ROLE_ADMISSION_OFFICER,
    ROLE_ACCOUNTANT,
    ROLE_HR_OFFICER,
    ROLE_TEACHER,
    ROLE_CLASS_TEACHER,
    ROLE_STUDENT,
    ROLE_PARENT,
]

# --- Permissions -----------------------------------------------------------
# Platform-level
P_PLATFORM_MANAGE = "platform.manage"
P_TENANT_VIEW = "tenant.view"
P_TENANT_CREATE = "tenant.create"
P_TENANT_EDIT = "tenant.edit"
P_TENANT_SUSPEND = "tenant.suspend"
P_AUDIT_VIEW_PLATFORM = "audit.view.platform"

# School-level
P_SCHOOL_VIEW = "school.view"
P_SCHOOL_EDIT = "school.edit"
P_USER_VIEW = "user.view"
P_USER_CREATE = "user.create"
P_USER_EDIT = "user.edit"
P_USER_DELETE = "user.delete"
P_ROLE_ASSIGN = "role.assign"
P_AUDIT_VIEW_SCHOOL = "audit.view.school"

# Future domain (declared so RBAC UI can toggle them)
P_STUDENT_VIEW = "student.view"
P_STUDENT_EDIT = "student.edit"
P_ATTENDANCE_OVERRIDE = "attendance.override"
P_FEES_COLLECT = "fees.collect"
P_FEES_REFUND = "fees.refund"
P_PAYROLL_PROCESS = "payroll.process"
P_EXAM_PUBLISH = "exam.publish"
P_LESSONPLAN_APPROVE = "lessonplan.approve"

# CRM (Prompt 2)
P_CRM_MANAGE = "crm.manage"       # legacy umbrella
P_CRM_CONVERT = "crm.convert"     # legacy umbrella
P_CRM_VIEW = "crm.view"
P_CRM_CREATE = "crm.create"
P_CRM_UPDATE = "crm.update"
P_CRM_DELETE = "crm.delete"
P_CRM_ASSIGN = "crm.assign"
P_CRM_ACTIVITY_CREATE = "crm.activity.create"
P_CRM_ACTIVITY_VIEW = "crm.activity.view"
P_CRM_STAGE_MANAGE = "crm.stage.manage"
P_CRM_CONFIG = "crm.config"

# Admissions (Prompt 2)
P_ADMISSION_VIEW = "admission.view"
P_ADMISSION_CREATE = "admission.create"
P_ADMISSION_UPDATE = "admission.update"
P_ADMISSION_REVIEW = "admission.review"
P_ADMISSION_APPROVE = "admission.approve"
P_ADMISSION_REJECT = "admission.reject"
P_ADMISSION_CONVERT = "admission.convert"
P_ADMISSION_OVERRIDE = "admission.override"  # override missing-documents block
P_ADMISSION_DOC_VIEW = "admission.document.view"
P_ADMISSION_DOC_UPLOAD = "admission.document.upload"
P_ADMISSION_DOC_VERIFY = "admission.document.verify"

# Student Master (Prompt 3)
P_STUDENT_STATUS_MANAGE = "student.status.manage"
P_STUDENT_ENROLL_VIEW = "student.enrollment.view"
P_STUDENT_ENROLL_MANAGE = "student.enrollment.manage"
P_STUDENT_GUARDIAN_VIEW = "student.guardian.view"
P_STUDENT_GUARDIAN_MANAGE = "student.guardian.manage"
P_STUDENT_DOC_VIEW = "student.document.view"
P_STUDENT_DOC_UPLOAD = "student.document.upload"
P_STUDENT_FAMILY_VIEW = "student.family.view"
P_STUDENT_FAMILY_MANAGE = "student.family.manage"
P_STUDENT_CREATE = "student.create"
P_STUDENT_UPDATE_NEW = "student.update"
P_GUARDIAN_VIEW = "guardian.view"
P_GUARDIAN_CREATE = "guardian.create"
P_GUARDIAN_UPDATE = "guardian.update"
P_FAMILY_VIEW = "family.view"
P_FAMILY_MANAGE = "family.manage"

STUDENT_PERMISSIONS = {
    P_STUDENT_STATUS_MANAGE, P_STUDENT_ENROLL_VIEW, P_STUDENT_ENROLL_MANAGE,
    P_STUDENT_GUARDIAN_VIEW, P_STUDENT_GUARDIAN_MANAGE, P_STUDENT_DOC_VIEW,
    P_STUDENT_DOC_UPLOAD, P_STUDENT_FAMILY_VIEW, P_STUDENT_FAMILY_MANAGE,
    P_STUDENT_CREATE, P_STUDENT_UPDATE_NEW,
    P_GUARDIAN_VIEW, P_GUARDIAN_CREATE, P_GUARDIAN_UPDATE,
    P_FAMILY_VIEW, P_FAMILY_MANAGE,
}

# Backwards-compat alias — Prompt 2 tests import P_STUDENT_UPDATE.
P_STUDENT_UPDATE = P_STUDENT_UPDATE_NEW


# Academic Structure & Calendar (Prompt 4)
P_ACADEMIC_VIEW = "academic.view"
P_ACADEMIC_YEAR_MANAGE = "academic.year.manage"
P_ACADEMIC_CLASS_MANAGE = "academic.class.manage"
P_ACADEMIC_SECTION_MANAGE = "academic.section.manage"
P_ACADEMIC_SUBJECT_MANAGE = "academic.subject.manage"
P_ACADEMIC_ROOM_MANAGE = "academic.room.manage"
P_ACADEMIC_SCHEDULE_MANAGE = "academic.schedule.manage"
P_ACADEMIC_CALENDAR_MANAGE = "academic.calendar.manage"
P_ACADEMIC_ASSIGN_MANAGE = "academic.assignment.manage"
P_ACADEMIC_BOARD_CONFIG = "academic.board.config"

ACADEMIC_PERMISSIONS = {
    P_ACADEMIC_VIEW, P_ACADEMIC_YEAR_MANAGE, P_ACADEMIC_CLASS_MANAGE,
    P_ACADEMIC_SECTION_MANAGE, P_ACADEMIC_SUBJECT_MANAGE, P_ACADEMIC_ROOM_MANAGE,
    P_ACADEMIC_SCHEDULE_MANAGE, P_ACADEMIC_CALENDAR_MANAGE,
    P_ACADEMIC_ASSIGN_MANAGE, P_ACADEMIC_BOARD_CONFIG,
}


# Staff Master + Leave (Prompt 5)
P_STAFF_VIEW = "staff.view"
P_STAFF_CREATE = "staff.create"
P_STAFF_UPDATE = "staff.update"
P_STAFF_STATUS_MANAGE = "staff.status.manage"
P_STAFF_DOC_VIEW = "staff.document.view"
P_STAFF_DOC_UPLOAD = "staff.document.upload"
P_STAFF_QUALIFICATION_MANAGE = "staff.qualification.manage"
P_STAFF_DEPARTMENT_MANAGE = "staff.department.manage"
P_STAFF_DESIGNATION_MANAGE = "staff.designation.manage"

P_LEAVE_TYPE_MANAGE = "leave.type.manage"
P_LEAVE_VIEW = "leave.view"
P_LEAVE_APPLY = "leave.apply"
P_LEAVE_APPROVE = "leave.approve"
P_LEAVE_ADJUST = "leave.adjust"
P_LEAVE_BALANCE_VIEW = "leave.balance.view"

STAFF_PERMISSIONS = {
    P_STAFF_VIEW, P_STAFF_CREATE, P_STAFF_UPDATE, P_STAFF_STATUS_MANAGE,
    P_STAFF_DOC_VIEW, P_STAFF_DOC_UPLOAD, P_STAFF_QUALIFICATION_MANAGE,
    P_STAFF_DEPARTMENT_MANAGE, P_STAFF_DESIGNATION_MANAGE,
    P_LEAVE_TYPE_MANAGE, P_LEAVE_VIEW, P_LEAVE_APPLY,
    P_LEAVE_APPROVE, P_LEAVE_ADJUST, P_LEAVE_BALANCE_VIEW,
}

CRM_PERMISSIONS = {
    P_CRM_MANAGE, P_CRM_CONVERT, P_CRM_VIEW, P_CRM_CREATE, P_CRM_UPDATE,
    P_CRM_DELETE, P_CRM_ASSIGN, P_CRM_ACTIVITY_CREATE, P_CRM_ACTIVITY_VIEW,
    P_CRM_STAGE_MANAGE, P_CRM_CONFIG,
}

ADMISSION_PERMISSIONS = {
    P_ADMISSION_VIEW, P_ADMISSION_CREATE, P_ADMISSION_UPDATE,
    P_ADMISSION_REVIEW, P_ADMISSION_APPROVE, P_ADMISSION_REJECT,
    P_ADMISSION_CONVERT, P_ADMISSION_OVERRIDE, P_ADMISSION_DOC_VIEW,
    P_ADMISSION_DOC_UPLOAD, P_ADMISSION_DOC_VERIFY,
}

ALL_PERMISSIONS = [
    # Platform
    P_PLATFORM_MANAGE, P_TENANT_VIEW, P_TENANT_CREATE, P_TENANT_EDIT,
    P_TENANT_SUSPEND, P_AUDIT_VIEW_PLATFORM,
    # School core
    P_SCHOOL_VIEW, P_SCHOOL_EDIT,
    P_USER_VIEW, P_USER_CREATE, P_USER_EDIT, P_USER_DELETE, P_ROLE_ASSIGN,
    P_AUDIT_VIEW_SCHOOL,
    # Domains (student stub)
    P_STUDENT_VIEW, P_STUDENT_EDIT, P_ATTENDANCE_OVERRIDE,
    P_FEES_COLLECT, P_FEES_REFUND, P_PAYROLL_PROCESS,
    P_EXAM_PUBLISH, P_LESSONPLAN_APPROVE,
    # CRM + Admission
    *sorted(CRM_PERMISSIONS),
    *sorted(ADMISSION_PERMISSIONS),
    # Student Master
    *sorted(STUDENT_PERMISSIONS),
    # Academic Structure
    *sorted(ACADEMIC_PERMISSIONS),
    # Staff Master + Leave
    *sorted(STAFF_PERMISSIONS),
]

# --- Role → Permissions ---------------------------------------------------
_FULL_CRM = set(CRM_PERMISSIONS)
_FULL_ADMISSION = set(ADMISSION_PERMISSIONS)

_ADMISSION_OFFICER = {
    P_SCHOOL_VIEW, P_USER_VIEW,
    # CRM full for their day-to-day work
    P_CRM_VIEW, P_CRM_CREATE, P_CRM_UPDATE, P_CRM_ASSIGN,
    P_CRM_ACTIVITY_CREATE, P_CRM_ACTIVITY_VIEW,
    P_CRM_MANAGE,  # backwards compat
    # Admissions — everything except approve/reject/convert/override
    P_ADMISSION_VIEW, P_ADMISSION_CREATE, P_ADMISSION_UPDATE,
    P_ADMISSION_REVIEW, P_ADMISSION_DOC_VIEW, P_ADMISSION_DOC_UPLOAD,
    P_ADMISSION_DOC_VERIFY,
    P_STUDENT_VIEW,
    P_ACADEMIC_VIEW,
}

_SCHOOL_ADMIN_BASE = {
    P_SCHOOL_VIEW, P_SCHOOL_EDIT,
    P_USER_VIEW, P_USER_CREATE, P_USER_EDIT, P_USER_DELETE, P_ROLE_ASSIGN,
    P_AUDIT_VIEW_SCHOOL,
    P_STUDENT_VIEW, P_STUDENT_EDIT,
    P_ATTENDANCE_OVERRIDE, P_FEES_COLLECT, P_FEES_REFUND,
    P_PAYROLL_PROCESS, P_EXAM_PUBLISH, P_LESSONPLAN_APPROVE,
    *_FULL_CRM, *_FULL_ADMISSION,
    *STUDENT_PERMISSIONS,
    *ACADEMIC_PERMISSIONS,
    *STAFF_PERMISSIONS,
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_PLATFORM_SUPERADMIN: set(ALL_PERMISSIONS),
    ROLE_SCHOOL_OWNER: _SCHOOL_ADMIN_BASE,
    ROLE_PRINCIPAL: _SCHOOL_ADMIN_BASE - {P_FEES_REFUND, P_PAYROLL_PROCESS, P_ADMISSION_OVERRIDE},
    ROLE_SCHOOL_ADMIN: _SCHOOL_ADMIN_BASE,
    ROLE_ADMISSION_OFFICER: _ADMISSION_OFFICER,
    ROLE_ACCOUNTANT: {
        P_SCHOOL_VIEW, P_USER_VIEW,
        P_FEES_COLLECT, P_FEES_REFUND, P_STUDENT_VIEW,
        # Accountants may VIEW admission status for fees follow-up — read-only.
        P_ADMISSION_VIEW,
    },
    ROLE_HR_OFFICER: {P_SCHOOL_VIEW, P_USER_VIEW, P_PAYROLL_PROCESS, *STAFF_PERMISSIONS},
    ROLE_TEACHER: {
        P_SCHOOL_VIEW, P_STUDENT_VIEW, P_ACADEMIC_VIEW,
        P_STAFF_VIEW, P_LEAVE_APPLY, P_LEAVE_VIEW, P_LEAVE_BALANCE_VIEW,
    },
    ROLE_CLASS_TEACHER: {
        P_SCHOOL_VIEW, P_STUDENT_VIEW, P_ACADEMIC_VIEW,
        P_STAFF_VIEW, P_LEAVE_APPLY, P_LEAVE_VIEW, P_LEAVE_BALANCE_VIEW,
        P_ATTENDANCE_OVERRIDE, P_LESSONPLAN_APPROVE,
    },
    ROLE_STUDENT: {P_SCHOOL_VIEW},
    ROLE_PARENT: {P_SCHOOL_VIEW},
}


def permissions_for(role: str) -> set[str]:
    return set(ROLE_PERMISSIONS.get(role, set()))


def has_permission(role: str, permission: str) -> bool:
    return permission in permissions_for(role)


def is_platform_role(role: str) -> bool:
    return role == ROLE_PLATFORM_SUPERADMIN
