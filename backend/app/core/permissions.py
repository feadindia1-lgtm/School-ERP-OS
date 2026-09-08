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

# Future domain permissions (registered so RBAC UI can show/toggle them)
P_STUDENT_VIEW = "student.view"
P_STUDENT_EDIT = "student.edit"
P_ATTENDANCE_OVERRIDE = "attendance.override"
P_FEES_COLLECT = "fees.collect"
P_FEES_REFUND = "fees.refund"
P_PAYROLL_PROCESS = "payroll.process"
P_EXAM_PUBLISH = "exam.publish"
P_LESSONPLAN_APPROVE = "lessonplan.approve"
P_CRM_MANAGE = "crm.manage"
P_CRM_CONVERT = "crm.convert"

ALL_PERMISSIONS = [
    P_PLATFORM_MANAGE, P_TENANT_VIEW, P_TENANT_CREATE, P_TENANT_EDIT,
    P_TENANT_SUSPEND, P_AUDIT_VIEW_PLATFORM,
    P_SCHOOL_VIEW, P_SCHOOL_EDIT,
    P_USER_VIEW, P_USER_CREATE, P_USER_EDIT, P_USER_DELETE, P_ROLE_ASSIGN,
    P_AUDIT_VIEW_SCHOOL,
    P_STUDENT_VIEW, P_STUDENT_EDIT, P_ATTENDANCE_OVERRIDE,
    P_FEES_COLLECT, P_FEES_REFUND, P_PAYROLL_PROCESS,
    P_EXAM_PUBLISH, P_LESSONPLAN_APPROVE,
    P_CRM_MANAGE, P_CRM_CONVERT,
]

# --- Role → Permissions ---------------------------------------------------
_SCHOOL_ADMIN_BASE = {
    P_SCHOOL_VIEW, P_SCHOOL_EDIT,
    P_USER_VIEW, P_USER_CREATE, P_USER_EDIT, P_USER_DELETE, P_ROLE_ASSIGN,
    P_AUDIT_VIEW_SCHOOL,
    P_STUDENT_VIEW, P_STUDENT_EDIT,
    P_ATTENDANCE_OVERRIDE, P_FEES_COLLECT, P_FEES_REFUND,
    P_PAYROLL_PROCESS, P_EXAM_PUBLISH, P_LESSONPLAN_APPROVE,
    P_CRM_MANAGE, P_CRM_CONVERT,
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_PLATFORM_SUPERADMIN: set(ALL_PERMISSIONS),
    ROLE_SCHOOL_OWNER: _SCHOOL_ADMIN_BASE,
    ROLE_PRINCIPAL: _SCHOOL_ADMIN_BASE - {P_FEES_REFUND, P_PAYROLL_PROCESS},
    ROLE_SCHOOL_ADMIN: _SCHOOL_ADMIN_BASE,
    ROLE_ADMISSION_OFFICER: {
        P_SCHOOL_VIEW, P_USER_VIEW,
        P_CRM_MANAGE, P_CRM_CONVERT, P_STUDENT_VIEW,
    },
    ROLE_ACCOUNTANT: {
        P_SCHOOL_VIEW, P_USER_VIEW,
        P_FEES_COLLECT, P_FEES_REFUND, P_STUDENT_VIEW,
    },
    ROLE_HR_OFFICER: {P_SCHOOL_VIEW, P_USER_VIEW, P_PAYROLL_PROCESS},
    ROLE_TEACHER: {P_SCHOOL_VIEW, P_STUDENT_VIEW},
    ROLE_CLASS_TEACHER: {
        P_SCHOOL_VIEW, P_STUDENT_VIEW,
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
