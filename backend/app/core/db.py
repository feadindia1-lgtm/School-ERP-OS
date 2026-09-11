"""MongoDB client shared across the application."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URL)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.DB_NAME]


async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def ensure_indexes() -> None:
    db = get_db()
    # Users: unique per email within a tenant scope (platform users have tenant_id=None)
    await db.users.create_index(
        [("email", 1), ("tenant_id", 1)], unique=True, name="uniq_email_per_tenant"
    )
    await db.users.create_index("tenant_id")
    await db.tenants.create_index("slug", unique=True)
    await db.tenants.create_index("school_code", sparse=True)
    await db.tenants.create_index("status")
    await db.audit_logs.create_index([("tenant_id", 1), ("created_at", -1)])
    await db.audit_logs.create_index("actor_id")
    await db.alerts.create_index([("tenant_id", 1), ("acknowledged", 1), ("created_at", -1)])
    await db.login_attempts.create_index("identifier")
    await db.login_attempts.create_index("last_attempt", expireAfterSeconds=86400)
    await db.password_reset_tokens.create_index(
        "expires_at", expireAfterSeconds=0
    )
    await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.refresh_tokens.create_index("jti", unique=True)

    # CRM
    await db.crm_leads.create_index([("tenant_id", 1), ("created_at", -1)])
    await db.crm_leads.create_index([("tenant_id", 1), ("stage", 1)])
    await db.crm_leads.create_index([("tenant_id", 1), ("assigned_to", 1)])
    await db.crm_leads.create_index([("tenant_id", 1), ("parent_mobile", 1)])
    await db.crm_leads.create_index([("tenant_id", 1), ("parent_email", 1)])
    await db.crm_leads.create_index([("tenant_id", 1), ("inquiry_number", 1)], unique=True, sparse=True)
    await db.crm_leads.create_index([("tenant_id", 1), ("academic_year", 1)])
    await db.crm_leads.create_index([("tenant_id", 1), ("next_followup_at", 1)])
    await db.crm_activities.create_index([("tenant_id", 1), ("lead_id", 1), ("created_at", -1)])
    await db.followups.create_index([("tenant_id", 1), ("assigned_to", 1), ("due_at", 1)])
    await db.followups.create_index([("tenant_id", 1), ("status", 1), ("due_at", 1)])
    await db.campus_visits.create_index([("tenant_id", 1), ("scheduled_date", 1)])
    await db.campus_visits.create_index([("tenant_id", 1), ("assigned_staff_id", 1), ("scheduled_date", 1)])

    # Admissions
    await db.admission_applications.create_index([("tenant_id", 1), ("created_at", -1)])
    await db.admission_applications.create_index([("tenant_id", 1), ("status", 1)])
    await db.admission_applications.create_index([("tenant_id", 1), ("academic_year", 1)])
    await db.admission_applications.create_index([("tenant_id", 1), ("application_number", 1)], unique=True, sparse=True)
    await db.admission_applications.create_index([("tenant_id", 1), ("lead_id", 1)])
    await db.admission_documents.create_index([("tenant_id", 1), ("application_id", 1), ("type_code", 1)])
    await db.admission_conversions.create_index([("tenant_id", 1), ("application_id", 1)], unique=True)
    await db.admission_settings.create_index("tenant_id", unique=True)
    # Drop legacy Prompt-2 index if it exists (student_number no longer used by canonical Student).
    try:
        await db.students.drop_index("tenant_id_1_student_number_1")
    except Exception:
        pass
    # Only admission_number is authoritative on the canonical Student Master.
    await db.students.create_index(
        [("tenant_id", 1), ("admission_number", 1)],
        unique=True,
        partialFilterExpression={"admission_number": {"$exists": True, "$type": "string"}},
        name="uniq_admission_per_tenant",
    )
    await db.students.create_index([("tenant_id", 1), ("status", 1)])
    await db.students.create_index([("tenant_id", 1), ("academic_year", 1), ("class_name", 1)])
    await db.students.create_index([("tenant_id", 1), ("family_id", 1)])
    await db.students.create_index([("tenant_id", 1), ("application_id", 1)])
    await db.guardians.create_index([("tenant_id", 1), ("mobile_primary", 1)])
    await db.guardians.create_index([("tenant_id", 1), ("email", 1)])
    await db.guardians.create_index([("tenant_id", 1), ("family_id", 1)])
    await db.student_guardians.create_index([("tenant_id", 1), ("student_id", 1)])
    await db.student_guardians.create_index([("tenant_id", 1), ("guardian_id", 1)])
    await db.student_enrollments.create_index([("tenant_id", 1), ("student_id", 1), ("academic_year", 1)])
    await db.student_enrollments.create_index([("tenant_id", 1), ("academic_year", 1), ("class_name", 1)])
    await db.families.create_index([("tenant_id", 1), ("family_name", 1)])
    # Counters — single-doc per tenant/prefix/year, so plain _id is sufficient

    # --- Academic Structure (Prompt 4) ---
    await db.academic_years.create_index([("tenant_id", 1), ("name", 1)], unique=True, name="uniq_academic_year")
    await db.academic_years.create_index([("tenant_id", 1), ("is_current", 1)])
    await db.board_configs.create_index("tenant_id", unique=True)
    await db.academic_classes.create_index([("tenant_id", 1), ("academic_year_id", 1), ("code", 1)], unique=True, name="uniq_class_code")
    await db.academic_classes.create_index([("tenant_id", 1), ("academic_year_id", 1), ("order", 1)])
    await db.academic_sections.create_index(
        [("tenant_id", 1), ("class_id", 1), ("name", 1)],
        unique=True, name="uniq_section_per_class",
    )
    await db.academic_sections.create_index([("tenant_id", 1), ("academic_year_id", 1)])
    await db.subjects.create_index([("tenant_id", 1), ("code", 1)], unique=True, name="uniq_subject_code")
    await db.subjects.create_index([("tenant_id", 1), ("name", 1)])
    await db.subject_groups.create_index([("tenant_id", 1), ("academic_year_id", 1), ("class_id", 1)])
    await db.rooms.create_index([("tenant_id", 1), ("code", 1)], unique=True, name="uniq_room_code")
    await db.rooms.create_index([("tenant_id", 1), ("room_type", 1)])
    await db.bell_schedules.create_index([("tenant_id", 1), ("academic_year_id", 1), ("name", 1)], unique=True, name="uniq_bell_schedule")
    await db.working_day_policies.create_index([("tenant_id", 1), ("academic_year_id", 1)], unique=True, name="uniq_working_day_policy")
    await db.holidays.create_index([("tenant_id", 1), ("academic_year_id", 1), ("start_date", 1)])
    await db.teacher_assignments.create_index(
        [("tenant_id", 1), ("academic_year_id", 1), ("teacher_user_id", 1),
         ("class_id", 1), ("section_id", 1), ("subject_id", 1)],
        unique=True, name="uniq_teacher_assignment",
    )
    await db.teacher_assignments.create_index([("tenant_id", 1), ("class_id", 1), ("section_id", 1)])
