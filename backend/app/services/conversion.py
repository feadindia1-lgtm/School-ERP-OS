"""Admission → Student conversion service.

Idempotent: a repeat convert() on the same application returns the existing conversion.
"""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.core.db import get_db
from app.models.admission import (
    APP_APPROVED, APP_CONVERTED, AdmissionConversion, GuardianStub, StudentStub,
    DOC_VERIFIED,
)
from app.services.numbering import next_number
from app.services.audit_service import log_event


async def convert_application_to_student(
    *, application_id: str, tenant_id: str, actor: dict, request=None,
    override_docs: bool = False,
) -> dict:
    db = get_db()
    from bson import ObjectId

    try:
        oid = ObjectId(application_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Application not found")

    app = await db.admission_applications.find_one({"_id": oid, "tenant_id": tenant_id})
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Idempotency — return existing conversion if already converted.
    if app.get("status") == APP_CONVERTED and app.get("student_id"):
        existing = await db.admission_conversions.find_one({
            "application_id": application_id, "tenant_id": tenant_id,
        })
        if existing:
            return {
                "application_id": application_id,
                "student_id": app["student_id"],
                "student_number": app.get("student_number"),
                "conversion_id": str(existing["_id"]),
                "already_converted": True,
            }

    if app.get("status") != APP_APPROVED:
        raise HTTPException(status_code=409, detail=f"Only APPROVED applications can be converted (current: {app.get('status')})")

    # Required-documents guard (bypassable with admission.override permission — checked in route).
    settings = await db.admission_settings.find_one({"tenant_id": tenant_id})
    require_docs = (settings or {}).get("require_docs_for_approval", True)
    if require_docs and not override_docs:
        required_types = [t["code"] for t in (settings or {}).get("doc_types", []) if t.get("requirement") == "required" and t.get("active", True)]
        if required_types:
            verified = await db.admission_documents.count_documents({
                "tenant_id": tenant_id, "application_id": application_id,
                "type_code": {"$in": required_types}, "status": DOC_VERIFIED,
            })
            if verified < len(required_types):
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot convert: {len(required_types) - verified} required document(s) not verified",
                )

    student_number = await next_number(tenant_id, "STU", width=6)

    student_doc = StudentStub(
        tenant_id=tenant_id,
        student_number=student_number,
        first_name=app["student_first_name"],
        last_name=app["student_last_name"],
        date_of_birth=app.get("student_dob"),
        gender=app.get("student_gender"),
        academic_year=app["academic_year"],
        class_name=app["class_requested"],
        application_id=application_id,
    ).to_mongo()
    stu_res = await db.students.insert_one(student_doc)
    student_id = str(stu_res.inserted_id)

    guardian_doc = GuardianStub(
        tenant_id=tenant_id,
        student_id=student_id,
        name=app["parent_name"],
        relationship=app.get("parent_relationship", "guardian"),
        mobile=app["parent_mobile"],
        email=app.get("parent_email"),
    ).to_mongo()
    g_res = await db.guardians.insert_one(guardian_doc)
    guardian_id = str(g_res.inserted_id)

    now = datetime.now(timezone.utc).isoformat()
    conv_doc = AdmissionConversion(
        tenant_id=tenant_id,
        application_id=application_id,
        lead_id=app.get("lead_id"),
        student_id=student_id,
        student_number=student_number,
        guardian_ids=[guardian_id],
        converted_by=actor["id"],
        metadata={"override_docs": bool(override_docs)},
    ).to_mongo()
    c_res = await db.admission_conversions.insert_one(conv_doc)

    await db.admission_applications.update_one(
        {"_id": oid, "tenant_id": tenant_id},
        {"$set": {"status": APP_CONVERTED, "student_id": student_id,
                  "student_number": student_number, "converted_at": now}},
    )
    if app.get("lead_id"):
        try:
            lead_oid = ObjectId(app["lead_id"])
            await db.crm_leads.update_one(
                {"_id": lead_oid, "tenant_id": tenant_id},
                {"$set": {"student_id": student_id, "converted_at": now, "stage": "ADMITTED"}},
            )
        except Exception:
            pass

    await log_event(
        action="admission.convert", resource="application", resource_id=application_id,
        tenant_id=tenant_id, actor=actor, request=request,
        new_value={"student_id": student_id, "student_number": student_number},
        metadata={"override_docs": bool(override_docs), "conversion_id": str(c_res.inserted_id)},
    )
    return {
        "application_id": application_id,
        "student_id": student_id,
        "student_number": student_number,
        "conversion_id": str(c_res.inserted_id),
        "already_converted": False,
    }
