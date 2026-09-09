"""Admission → Student Master conversion.

Idempotent: rerunning on the same application returns the existing student
without creating another.  Uses the canonical `students` / `guardians`
collections (evolved Prompt-2 stubs) plus `student_guardians`,
`student_enrollments`, `families`, `admission_conversions`.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from app.core.db import get_db
from app.models.admission import (
    APP_APPROVED, APP_CONVERTED, AdmissionConversion, DOC_VERIFIED,
)
from app.models.student import (
    Family, Guardian, Student, StudentEnrollment, StudentGuardian,
)
from app.services.audit_service import log_event
from app.services.numbering import next_number


async def convert_application_to_student(
    *, application_id: str, tenant_id: str, actor: dict, request=None,
    override_docs: bool = False,
) -> dict:
    db = get_db()

    try:
        oid = ObjectId(application_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Application not found")

    app = await db.admission_applications.find_one({"_id": oid, "tenant_id": tenant_id})
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Idempotency
    if app.get("status") == APP_CONVERTED and app.get("student_id"):
        existing = await db.admission_conversions.find_one({
            "application_id": application_id, "tenant_id": tenant_id,
        })
        if existing:
            return {
                "application_id": application_id, "student_id": app["student_id"],
                "student_number": app.get("student_number"),
                "conversion_id": str(existing["_id"]), "already_converted": True,
            }

    if app.get("status") != APP_APPROVED:
        raise HTTPException(status_code=409, detail=f"Only APPROVED applications can be converted (current: {app.get('status')})")

    settings = await db.admission_settings.find_one({"tenant_id": tenant_id})
    require_docs = (settings or {}).get("require_docs_for_approval", True)
    if require_docs and not override_docs:
        required = [t["code"] for t in (settings or {}).get("doc_types", []) if t.get("requirement") == "required" and t.get("active", True)]
        if required:
            verified = await db.admission_documents.count_documents({
                "tenant_id": tenant_id, "application_id": application_id,
                "type_code": {"$in": required}, "status": DOC_VERIFIED,
            })
            if verified < len(required):
                raise HTTPException(status_code=409, detail=f"Cannot convert: {len(required) - verified} required document(s) not verified")

    # 1. Student (canonical Student Master)
    admission_number = await next_number(tenant_id, "STU", width=6)
    now = datetime.now(timezone.utc).isoformat()
    student_doc = Student(
        tenant_id=tenant_id, admission_number=admission_number,
        first_name=app["student_first_name"], last_name=app.get("student_last_name"),
        date_of_birth=app.get("student_dob"), gender=app.get("student_gender"),
        academic_year=app["academic_year"], class_name=app["class_requested"],
        application_id=application_id, lead_id=app.get("lead_id"),
        admission_date=now, status="ACTIVE", status_effective_date=now,
    ).to_mongo()
    stu_res = await db.students.insert_one(student_doc)
    student_id = str(stu_res.inserted_id)

    # 2. Guardian — reuse existing one for the same tenant + mobile when possible.
    existing_g = await db.guardians.find_one({
        "tenant_id": tenant_id, "mobile_primary": app["parent_mobile"],
    })
    if existing_g:
        guardian_id = str(existing_g["_id"])
    else:
        g_doc = Guardian(
            tenant_id=tenant_id,
            first_name=(app["parent_name"].split(" ", 1)[0] if app.get("parent_name") else "Guardian"),
            last_name=(app["parent_name"].split(" ", 1)[1] if app.get("parent_name") and " " in app["parent_name"] else None),
            relationship_type=app.get("parent_relationship", "guardian"),
            mobile_primary=app["parent_mobile"],
            email=(app.get("parent_email") or None),
        ).to_mongo()
        g_res = await db.guardians.insert_one(g_doc)
        guardian_id = str(g_res.inserted_id)

    # 3. Student-Guardian relationship
    sg_doc = StudentGuardian(
        tenant_id=tenant_id, student_id=student_id, guardian_id=guardian_id,
        relationship_type=app.get("parent_relationship", "guardian"),
        is_primary=True, is_emergency_contact=True,
        has_pickup_authorization=True, has_fee_responsibility=True,
        has_academic_access=True, start_date=now,
    ).to_mongo()
    sg_res = await db.student_guardians.insert_one(sg_doc)

    # 4. Enrollment history
    enr_doc = StudentEnrollment(
        tenant_id=tenant_id, student_id=student_id,
        academic_year=app["academic_year"], class_name=app["class_requested"],
        enrollment_status="active", start_date=now,
    ).to_mongo()
    enr_res = await db.student_enrollments.insert_one(enr_doc)

    # 5. Conversion record
    conv = AdmissionConversion(
        tenant_id=tenant_id, application_id=application_id,
        lead_id=app.get("lead_id"), student_id=student_id,
        student_number=admission_number, guardian_ids=[guardian_id],
        converted_by=actor["id"],
        metadata={"override_docs": bool(override_docs), "enrollment_id": str(enr_res.inserted_id),
                  "student_guardian_id": str(sg_res.inserted_id)},
    ).to_mongo()
    c_res = await db.admission_conversions.insert_one(conv)

    # 6. Update application + lead
    await db.admission_applications.update_one(
        {"_id": oid, "tenant_id": tenant_id},
        {"$set": {"status": APP_CONVERTED, "student_id": student_id,
                  "student_number": admission_number, "converted_at": now}},
    )
    if app.get("lead_id"):
        try:
            await db.crm_leads.update_one(
                {"_id": ObjectId(app["lead_id"]), "tenant_id": tenant_id},
                {"$set": {"student_id": student_id, "converted_at": now, "stage": "ADMITTED"}},
            )
        except Exception:
            pass

    await log_event(
        action="admission.convert", resource="application", resource_id=application_id,
        tenant_id=tenant_id, actor=actor, request=request,
        new_value={"student_id": student_id, "admission_number": admission_number},
        metadata={"conversion_id": str(c_res.inserted_id), "guardian_id": guardian_id,
                  "override_docs": bool(override_docs)},
    )
    return {
        "application_id": application_id, "student_id": student_id,
        "student_number": admission_number, "conversion_id": str(c_res.inserted_id),
        "already_converted": False,
    }
