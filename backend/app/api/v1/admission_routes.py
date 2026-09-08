"""Admission routes — applications, documents, review, conversion."""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from app.api.v1.schemas_crm import (
    ApplicationOut, ApplicationStatusChange, ConversionResult, ConvertRequest,
    CreateApplicationRequest, DocumentOut, DocumentVerifyRequest, PagedApplications,
    UpdateApplicationRequest,
)
from app.core.db import get_db
from app.core.deps import require_permission
from app.core.permissions import (
    P_ADMISSION_APPROVE, P_ADMISSION_CONVERT, P_ADMISSION_CREATE, P_ADMISSION_DOC_UPLOAD,
    P_ADMISSION_DOC_VERIFY, P_ADMISSION_DOC_VIEW, P_ADMISSION_OVERRIDE, P_ADMISSION_REJECT,
    P_ADMISSION_REVIEW, P_ADMISSION_UPDATE, P_ADMISSION_VIEW, permissions_for,
)
from app.models.admission import (
    APP_APPROVED, APP_CONVERTED, APP_DRAFT, APP_REJECTED, APP_STATES, APP_SUBMITTED,
    APP_TRANSITIONS, DOC_PENDING, DOC_REJECTED, DOC_STATUSES, DOC_VERIFIED,
    AdmissionApplication, AdmissionDocument,
)
from app.services.audit_service import log_event
from app.services.conversion import convert_application_to_student
from app.services.numbering import next_number
from app.services.storage import storage

router = APIRouter(prefix="/school/admissions", tags=["admissions"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME = {
    "application/pdf", "image/jpeg", "image/jpg", "image/png", "image/webp",
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _oid(v: str) -> ObjectId:
    try:
        return ObjectId(v)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Not found")


def _app_out(d: dict) -> ApplicationOut:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return ApplicationOut(**d)


def _doc_out(d: dict) -> DocumentOut:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    d.pop("storage_key", None)
    d.pop("tenant_id", None)
    return DocumentOut(**d)


async def _ensure_settings(tenant_id: str) -> dict:
    """Local mirror of crm_routes._ensure_settings to avoid circular import."""
    from app.api.v1.crm_routes import _ensure_settings as ensure
    return await ensure(tenant_id)


# ============================================================
# Applications
# ============================================================
@router.post("/applications", response_model=ApplicationOut, status_code=201)
async def create_application(
    payload: CreateApplicationRequest, request: Request,
    user: dict = Depends(require_permission(P_ADMISSION_CREATE)),
):
    db = get_db()
    lead = None
    if payload.lead_id:
        lead = await db.crm_leads.find_one({"_id": _oid(payload.lead_id), "tenant_id": user["tenant_id"]})
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if lead.get("application_id"):
            raise HTTPException(status_code=409, detail="Lead already has an application", headers={"X-Existing-App": lead["application_id"]})

    app_number = await next_number(user["tenant_id"], "ADM")
    doc = AdmissionApplication(
        tenant_id=user["tenant_id"], application_number=app_number,
        lead_id=payload.lead_id,
        academic_year=payload.academic_year, class_requested=payload.class_requested,
        student_first_name=payload.student_first_name, student_last_name=payload.student_last_name,
        student_dob=payload.student_dob, student_gender=payload.student_gender,
        previous_school=payload.previous_school,
        parent_name=payload.parent_name, parent_relationship=payload.parent_relationship,
        parent_mobile=payload.parent_mobile,
        parent_email=payload.parent_email.lower() if payload.parent_email else None,
    ).to_mongo()
    res = await db.admission_applications.insert_one(doc)
    doc["_id"] = res.inserted_id

    if payload.lead_id:
        await db.crm_leads.update_one({"_id": _oid(payload.lead_id)}, {"$set": {
            "application_id": str(res.inserted_id),
            "stage": "FORM_FILLED",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }})

    # Seed document rows for required + optional configured types
    settings = await _ensure_settings(user["tenant_id"])
    for dt in settings.get("doc_types", []):
        if not dt.get("active", True):
            continue
        await db.admission_documents.insert_one(AdmissionDocument(
            tenant_id=user["tenant_id"], application_id=str(res.inserted_id),
            type_code=dt["code"], type_label=dt["label"],
            status=DOC_PENDING if dt.get("requirement") != "optional" else DOC_PENDING,
        ).to_mongo())

    await log_event(
        action="admission.application.create", resource="application",
        resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
        actor=user, request=request,
        new_value={"application_number": app_number, "class_requested": payload.class_requested,
                   "academic_year": payload.academic_year, "lead_id": payload.lead_id},
    )
    return _app_out(doc)


@router.get("/applications", response_model=PagedApplications)
async def list_applications(
    q: str | None = None, status: str | None = None,
    academic_year: str | None = None, class_requested: str | None = None,
    assigned_reviewer: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    user: dict = Depends(require_permission(P_ADMISSION_VIEW)),
):
    query: dict = {"tenant_id": user["tenant_id"]}
    if status:
        query["status"] = status
    if academic_year:
        query["academic_year"] = academic_year
    if class_requested:
        query["class_requested"] = class_requested
    if assigned_reviewer:
        query["assigned_reviewer"] = assigned_reviewer
    if q:
        rx = {"$regex": q, "$options": "i"}
        query["$or"] = [
            {"student_first_name": rx}, {"student_last_name": rx},
            {"parent_name": rx}, {"parent_mobile": rx},
            {"application_number": rx},
        ]
    db = get_db()
    total = await db.admission_applications.count_documents(query)
    docs = await db.admission_applications.find(query).sort("created_at", -1).skip((page-1)*page_size).limit(page_size).to_list(page_size)
    return PagedApplications(items=[_app_out(d) for d in docs], total=total, page=page, page_size=page_size)


@router.get("/applications/{app_id}", response_model=ApplicationOut)
async def get_application(app_id: str, user: dict = Depends(require_permission(P_ADMISSION_VIEW))):
    d = await get_db().admission_applications.find_one({"_id": _oid(app_id), "tenant_id": user["tenant_id"]})
    if not d:
        raise HTTPException(status_code=404, detail="Application not found")
    return _app_out(d)


@router.patch("/applications/{app_id}", response_model=ApplicationOut)
async def update_application(
    app_id: str, payload: UpdateApplicationRequest, request: Request,
    user: dict = Depends(require_permission(P_ADMISSION_UPDATE)),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if updates.get("parent_email"):
        updates["parent_email"] = updates["parent_email"].lower()
    db = get_db()
    old = await db.admission_applications.find_one({"_id": _oid(app_id), "tenant_id": user["tenant_id"]})
    if not old:
        raise HTTPException(status_code=404, detail="Application not found")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.admission_applications.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.admission_applications.find_one({"_id": old["_id"]})
    await log_event(
        action="admission.application.update", resource="application", resource_id=app_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={k: old.get(k) for k in updates.keys() if k != "updated_at"},
        new_value={k: v for k, v in updates.items() if k != "updated_at"},
    )
    return _app_out(new)


@router.post("/applications/{app_id}/status", response_model=ApplicationOut)
async def change_application_status(
    app_id: str, payload: ApplicationStatusChange, request: Request,
    user: dict = Depends(require_permission(P_ADMISSION_REVIEW)),
):
    if payload.status not in APP_STATES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {APP_STATES}")
    db = get_db()
    old = await db.admission_applications.find_one({"_id": _oid(app_id), "tenant_id": user["tenant_id"]})
    if not old:
        raise HTTPException(status_code=404, detail="Application not found")

    current = old.get("status", APP_DRAFT)
    if payload.status not in APP_TRANSITIONS.get(current, set()):
        raise HTTPException(status_code=409, detail=f"Cannot transition from {current} to {payload.status}")

    # Permission gate for terminal decisions
    user_perms = permissions_for(user["role"]) | set(user.get("extra_permissions", []))
    if payload.status == APP_APPROVED and P_ADMISSION_APPROVE not in user_perms:
        raise HTTPException(status_code=403, detail="Missing permission: admission.approve")
    if payload.status == APP_REJECTED and P_ADMISSION_REJECT not in user_perms:
        raise HTTPException(status_code=403, detail="Missing permission: admission.reject")
    if payload.status == APP_REJECTED and not (payload.reason or "").strip():
        raise HTTPException(status_code=400, detail="Rejection reason is required")

    # Approval requires verified required documents (unless overridden).
    if payload.status == APP_APPROVED:
        settings = await _ensure_settings(user["tenant_id"])
        required = [t["code"] for t in settings.get("doc_types", []) if t.get("requirement") == "required" and t.get("active", True)]
        if settings.get("require_docs_for_approval", True) and required:
            verified = await db.admission_documents.count_documents({
                "tenant_id": user["tenant_id"], "application_id": app_id,
                "type_code": {"$in": required}, "status": DOC_VERIFIED,
            })
            if verified < len(required):
                if P_ADMISSION_OVERRIDE not in user_perms:
                    raise HTTPException(status_code=409, detail=f"{len(required) - verified} required document(s) not verified — override permission needed")
                await log_event(
                    action="admission.override", resource="application", resource_id=app_id,
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    metadata={"reason": payload.reason, "missing_verified_required_docs": len(required) - verified},
                )

    updates = {"status": payload.status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if payload.review_notes is not None:
        updates["review_notes"] = payload.review_notes
    if payload.status == APP_SUBMITTED and not old.get("submitted_at"):
        updates["submitted_at"] = updates["updated_at"]
    if payload.status in {APP_APPROVED, APP_REJECTED}:
        updates["decision_at"] = updates["updated_at"]
        updates["decided_by"] = user["id"]
        if payload.status == APP_REJECTED:
            updates["rejection_reason"] = payload.reason

    await db.admission_applications.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.admission_applications.find_one({"_id": old["_id"]})

    # Propagate to CRM lead stage where meaningful
    if new.get("lead_id"):
        crm_stage = {APP_SUBMITTED: "FORM_FILLED", "UNDER_REVIEW": "UNDER_REVIEW",
                     APP_APPROVED: "APPROVED", APP_REJECTED: "LOST"}
        if payload.status in crm_stage:
            await db.crm_leads.update_one(
                {"_id": _oid(new["lead_id"]), "tenant_id": user["tenant_id"]},
                {"$set": {"stage": crm_stage[payload.status]}},
            )

    action_name = {APP_APPROVED: "admission.approve", APP_REJECTED: "admission.reject"}.get(payload.status, "admission.application.status")
    await log_event(
        action=action_name, resource="application", resource_id=app_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={"status": current}, new_value={"status": payload.status},
        metadata={"reason": payload.reason},
    )
    return _app_out(new)


# ============================================================
# Documents
# ============================================================
@router.get("/applications/{app_id}/documents", response_model=list[DocumentOut])
async def list_documents(app_id: str, user: dict = Depends(require_permission(P_ADMISSION_DOC_VIEW))):
    db = get_db()
    if not await db.admission_applications.find_one({"_id": _oid(app_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Application not found")
    docs = await db.admission_documents.find({"tenant_id": user["tenant_id"], "application_id": app_id}).sort("created_at", 1).to_list(200)
    return [_doc_out(d) for d in docs]


@router.post("/applications/{app_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    app_id: str, request: Request,
    type_code: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_permission(P_ADMISSION_DOC_UPLOAD)),
):
    db = get_db()
    app_doc = await db.admission_applications.find_one({"_id": _oid(app_id), "tenant_id": user["tenant_id"]})
    if not app_doc:
        raise HTTPException(status_code=404, detail="Application not found")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")

    settings = await _ensure_settings(user["tenant_id"])
    type_meta = next((t for t in settings.get("doc_types", []) if t["code"] == type_code), None)
    if not type_meta:
        raise HTTPException(status_code=400, detail="Unknown document type")

    existing = await db.admission_documents.find_one({
        "tenant_id": user["tenant_id"], "application_id": app_id, "type_code": type_code,
    })

    now = datetime.now(timezone.utc).isoformat()
    if existing:
        doc_id = str(existing["_id"])
        # Delete old file if any
        if existing.get("storage_key"):
            try:
                await storage.delete(user["tenant_id"], existing["storage_key"])
            except Exception:
                pass
        storage_key = await storage.put(user["tenant_id"], doc_id, content)
        await db.admission_documents.update_one({"_id": existing["_id"]}, {"$set": {
            "filename": file.filename, "content_type": file.content_type,
            "size_bytes": len(content), "storage_key": storage_key,
            "status": DOC_PENDING, "uploaded_by": user["id"], "uploaded_at": now,
            "verified_by": None, "verified_at": None, "rejection_reason": None,
            "updated_at": now,
        }})
        new = await db.admission_documents.find_one({"_id": existing["_id"]})
    else:
        doc = AdmissionDocument(
            tenant_id=user["tenant_id"], application_id=app_id,
            type_code=type_code, type_label=type_meta["label"],
            filename=file.filename, content_type=file.content_type,
            size_bytes=len(content), status=DOC_PENDING,
            uploaded_by=user["id"], uploaded_at=now,
        ).to_mongo()
        res = await db.admission_documents.insert_one(doc)
        doc_id = str(res.inserted_id)
        storage_key = await storage.put(user["tenant_id"], doc_id, content)
        await db.admission_documents.update_one({"_id": res.inserted_id}, {"$set": {"storage_key": storage_key}})
        new = await db.admission_documents.find_one({"_id": res.inserted_id})

    await log_event(
        action="admission.document.upload", resource="document", resource_id=doc_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        metadata={"application_id": app_id, "type_code": type_code, "size": len(content)},
    )
    return _doc_out(new)


@router.get("/applications/{app_id}/documents/{doc_id}/download")
async def download_document(
    app_id: str, doc_id: str,
    user: dict = Depends(require_permission(P_ADMISSION_DOC_VIEW)),
):
    db = get_db()
    d = await db.admission_documents.find_one({
        "_id": _oid(doc_id), "tenant_id": user["tenant_id"], "application_id": app_id,
    })
    if not d or not d.get("storage_key"):
        raise HTTPException(status_code=404, detail="Document not found")
    data = await storage.get(user["tenant_id"], d["storage_key"])
    return Response(
        content=data,
        media_type=d.get("content_type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{d.get("filename","document")}"'},
    )


@router.post("/applications/{app_id}/documents/{doc_id}/verify", response_model=DocumentOut)
async def verify_document(
    app_id: str, doc_id: str, payload: DocumentVerifyRequest, request: Request,
    user: dict = Depends(require_permission(P_ADMISSION_DOC_VERIFY)),
):
    if payload.status not in {DOC_VERIFIED, DOC_REJECTED}:
        raise HTTPException(status_code=400, detail=f"Status must be one of {DOC_VERIFIED} / {DOC_REJECTED}")
    if payload.status == DOC_REJECTED and not (payload.rejection_reason or "").strip():
        raise HTTPException(status_code=400, detail="Rejection reason is required")

    db = get_db()
    old = await db.admission_documents.find_one({
        "_id": _oid(doc_id), "tenant_id": user["tenant_id"], "application_id": app_id,
    })
    if not old:
        raise HTTPException(status_code=404, detail="Document not found")
    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "status": payload.status, "verified_by": user["id"], "verified_at": now,
        "rejection_reason": payload.rejection_reason if payload.status == DOC_REJECTED else None,
        "updated_at": now,
    }
    await db.admission_documents.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.admission_documents.find_one({"_id": old["_id"]})

    await log_event(
        action="admission.document.verify" if payload.status == DOC_VERIFIED else "admission.document.reject",
        resource="document", resource_id=doc_id, tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={"status": old.get("status")}, new_value={"status": payload.status},
        metadata={"application_id": app_id, "rejection_reason": payload.rejection_reason},
    )
    return _doc_out(new)


# ============================================================
# Conversion
# ============================================================
@router.post("/applications/{app_id}/convert", response_model=ConversionResult)
async def convert(
    app_id: str, payload: ConvertRequest, request: Request,
    user: dict = Depends(require_permission(P_ADMISSION_CONVERT)),
):
    user_perms = permissions_for(user["role"]) | set(user.get("extra_permissions", []))
    if payload.override_docs and P_ADMISSION_OVERRIDE not in user_perms:
        raise HTTPException(status_code=403, detail="Missing permission: admission.override")
    result = await convert_application_to_student(
        application_id=app_id, tenant_id=user["tenant_id"],
        actor=user, request=request, override_docs=payload.override_docs,
    )
    return ConversionResult(**result)
