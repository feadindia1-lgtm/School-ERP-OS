"""Stabilization Workstream D — applicant-facing admission form + secure document upload.

Staff router  (/school/admissions/...): form config, create/revoke applicant links.
Public router (/public/admissions/...): school form by slug, applicant token views.
Raw tokens are never stored — only their sha256. Files go through services.storage.
"""
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.api.v1.admission_routes import ALLOWED_MIME, MAX_UPLOAD_BYTES, create_application_record
from app.api.v1.crm_routes import _ensure_settings
from app.core.db import get_db
from app.core.deps import require_permission
from app.core.permissions import P_ADMISSION_CREATE, P_ADMISSION_VIEW, P_CRM_CONFIG, P_CRM_VIEW
from app.models.admission import (
    APP_DOCUMENTS_PENDING, APP_DRAFT, APP_SUBMITTED, APP_UNDER_REVIEW, DEFAULT_FORM_CONFIG,
    DOC_PENDING, DOC_VERIFIED, ApplicantLink,
)
from app.models.crm import CrmLead
from app.services.admission_flow import fee_required, sync_lead_from_application
from app.services.audit_service import log_event
from app.services.numbering import next_number
from app.services.storage import storage

staff_router = APIRouter(prefix="/school/admissions", tags=["applicant-links"])
public_router = APIRouter(prefix="/public/admissions", tags=["public-admissions"])

EDITABLE = {APP_DRAFT, APP_DOCUMENTS_PENDING}
UPLOADABLE = {APP_DRAFT, APP_SUBMITTED, APP_UNDER_REVIEW, APP_DOCUMENTS_PENDING}
OPTIONAL_FIELDS = ["student_dob", "student_gender", "previous_school", "parent_email", "address"]
MOBILE_RX = re.compile(r"^\+?[0-9 \-]{7,18}$")
PUBLIC_SUBMITS_PER_HOUR = 10


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _form_config(settings: dict) -> dict:
    cfg = {**DEFAULT_FORM_CONFIG, **(settings.get("form_config") or {})}
    cfg["fields"] = {**DEFAULT_FORM_CONFIG["fields"], **(cfg.get("fields") or {})}
    return cfg


async def _form_options(db, tid: str, cfg: dict) -> dict:
    years = cfg.get("academic_years") or [y["name"] for y in await db.academic_years.find(
        {"tenant_id": tid, "status": {"$ne": "archived"}}).sort("start_date", 1).to_list(20)]
    classes = cfg.get("classes")
    if not classes:
        yr = await db.academic_years.find_one({"tenant_id": tid, "status": {"$ne": "archived"}}, sort=[("is_current", -1), ("start_date", -1)])
        classes = [c["name"] for c in await db.academic_classes.find(
            {"tenant_id": tid, "academic_year_id": str(yr["_id"])}).sort("order", 1).to_list(100)] if yr else []
    return {"academic_years": years, "classes": classes}


def _doc_types(settings: dict) -> list[dict]:
    return [{"code": d["code"], "label": d["label"], "requirement": d.get("requirement", "required"),
             "condition_note": d.get("condition_note")} for d in settings.get("doc_types", []) if d.get("active", True)]


# ============================================================
# Staff: form config
# ============================================================
class FormConfigIn(BaseModel):
    enabled: bool = True
    intro_text: str | None = Field(default=None, max_length=1000)
    academic_years: list[str] = Field(default_factory=list)
    classes: list[str] = Field(default_factory=list)
    fields: dict = Field(default_factory=dict)
    custom_questions: list[dict] = Field(default_factory=list)
    link_expiry_days: int = Field(default=14, ge=1, le=90)


@staff_router.get("/form-config")
async def get_form_config(user: dict = Depends(require_permission(P_CRM_VIEW))):
    db = get_db(); tid = user["tenant_id"]
    cfg = _form_config(await _ensure_settings(tid))
    t = await db.tenants.find_one({"_id": ObjectId(tid)})
    return {**cfg, "public_path": f"/apply/{t.get('slug')}", "options": await _form_options(db, tid, cfg)}


@staff_router.put("/form-config")
async def put_form_config(payload: FormConfigIn, request: Request, user: dict = Depends(require_permission(P_CRM_CONFIG))):
    db = get_db(); tid = user["tenant_id"]
    fields = {k: {"enabled": bool(v.get("enabled", True)), "required": bool(v.get("required", False)) and bool(v.get("enabled", True))}
              for k, v in payload.fields.items() if k in OPTIONAL_FIELDS and isinstance(v, dict)}
    questions, used = [], set()
    for q in payload.custom_questions:
        label = str(q.get("label") or "").strip()[:200]
        if not label: continue
        key = str(q.get("key") or "")
        if not re.fullmatch(r"q_[a-z0-9]{6}", key) or key in used:
            key = f"q_{secrets.token_hex(3)}"
        used.add(key)
        qtype = q.get("type") if q.get("type") in {"text", "textarea", "select"} else "text"
        questions.append({"key": key, "label": label, "type": qtype,
                          "options": [str(o)[:100] for o in (q.get("options") or [])][:20] if qtype == "select" else [],
                          "required": bool(q.get("required"))})
    cfg = {**payload.model_dump(), "fields": fields, "custom_questions": questions}
    await _ensure_settings(tid)
    await db.admission_settings.update_one({"tenant_id": tid}, {"$set": {"form_config": cfg, "updated_at": _now().isoformat()}})
    await log_event(action="admission.form_config.update", resource="admission_settings", tenant_id=tid,
                    actor=user, request=request, new_value={"enabled": cfg["enabled"], "questions": len(questions)})
    return await get_form_config(user)


# ============================================================
# Staff: applicant links
# ============================================================
class LinkCreateIn(BaseModel):
    lead_id: str


async def _issue_link(db, tid: str, app_id: str, lead_id: str | None, kind: str, days: int, created_by: str | None) -> dict:
    await db.admission_links.update_many({"tenant_id": tid, "application_id": app_id, "status": "active"},
                                         {"$set": {"status": "revoked", "updated_at": _now().isoformat()}})
    token = secrets.token_urlsafe(32)
    expires = (_now() + timedelta(days=days)).isoformat()
    doc = ApplicantLink(tenant_id=tid, application_id=app_id, lead_id=lead_id, token_hash=_hash(token),
                        kind=kind, expires_at=expires, created_by=created_by).to_mongo()
    res = await db.admission_links.insert_one(doc)
    return {"link_id": str(res.inserted_id), "token": token, "url_path": f"/apply/t/{token}",
            "expires_at": expires, "application_id": app_id}


@staff_router.post("/applicant-links", status_code=201)
async def create_applicant_link(payload: LinkCreateIn, request: Request, user: dict = Depends(require_permission(P_ADMISSION_CREATE))):
    db = get_db(); tid = user["tenant_id"]
    if not ObjectId.is_valid(payload.lead_id): raise HTTPException(status_code=404, detail="Lead not found")
    lead = await db.crm_leads.find_one({"_id": ObjectId(payload.lead_id), "tenant_id": tid})
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    if lead.get("application_id"):
        app = await db.admission_applications.find_one({"_id": ObjectId(lead["application_id"]), "tenant_id": tid})
        if app["status"] not in UPLOADABLE:
            raise HTTPException(status_code=409, detail={"code": "application_closed",
                                "message": f"Application is {app['status']} — applicant links are only for open applications"})
    else:
        app = await create_application_record(db, tid, {
            "academic_year": lead.get("academic_year") or "", "class_requested": lead.get("class_seeking") or "",
            "student_first_name": lead["student_first_name"], "student_last_name": lead["student_last_name"],
            "student_dob": lead.get("student_dob"), "student_gender": lead.get("student_gender"),
            "previous_school": lead.get("previous_school"), "parent_name": lead["parent_name"],
            "parent_relationship": lead.get("parent_relationship", "guardian"), "parent_mobile": lead["parent_mobile"],
            "parent_email": lead.get("parent_email"),
        }, lead_id=payload.lead_id, actor_id=user["id"], app_number=await next_number(tid, "ADM"), submitted_via="applicant_link")
    cfg = _form_config(await _ensure_settings(tid))
    out = await _issue_link(db, tid, str(app["_id"]), payload.lead_id, "invite", cfg["link_expiry_days"], user["id"])
    await log_event(action="admission.applicant_link.create", resource="application", resource_id=out["application_id"],
                    tenant_id=tid, actor=user, request=request, metadata={"lead_id": payload.lead_id, "expires_at": out["expires_at"]})
    return out


@staff_router.get("/applications/{app_id}/applicant-links")
async def list_applicant_links(app_id: str, user: dict = Depends(require_permission(P_ADMISSION_VIEW))):
    docs = await get_db().admission_links.find({"tenant_id": user["tenant_id"], "application_id": app_id}).sort("created_at", -1).to_list(50)
    now = _now().isoformat()
    return [{"id": str(d["_id"]), "kind": d["kind"], "status": "expired" if d["status"] == "active" and d["expires_at"] < now else d["status"],
             "expires_at": d["expires_at"], "created_at": d.get("created_at"), "last_used_at": d.get("last_used_at")} for d in docs]


@staff_router.post("/applicant-links/{link_id}/revoke")
async def revoke_applicant_link(link_id: str, request: Request, user: dict = Depends(require_permission(P_ADMISSION_CREATE))):
    db = get_db()
    if not ObjectId.is_valid(link_id): raise HTTPException(status_code=404, detail="Link not found")
    res = await db.admission_links.update_one({"_id": ObjectId(link_id), "tenant_id": user["tenant_id"]},
                                              {"$set": {"status": "revoked", "updated_at": _now().isoformat()}})
    if not res.matched_count: raise HTTPException(status_code=404, detail="Link not found")
    await log_event(action="admission.applicant_link.revoke", resource="admission_link", resource_id=link_id,
                    tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Public: helpers
# ============================================================
class ApplicantForm(BaseModel):
    academic_year: str = Field(min_length=1, max_length=40)
    class_requested: str = Field(min_length=1, max_length=40)
    student_first_name: str = Field(min_length=1, max_length=80)
    student_last_name: str = Field(min_length=1, max_length=80)
    student_dob: str | None = Field(default=None, max_length=20)
    student_gender: str | None = Field(default=None, max_length=20)
    previous_school: str | None = Field(default=None, max_length=200)
    parent_name: str = Field(min_length=2, max_length=120)
    parent_relationship: str = Field(default="guardian", max_length=30)
    parent_mobile: str = Field(min_length=7, max_length=18)
    parent_email: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    form_answers: dict = Field(default_factory=dict)
    website: str | None = None   # honeypot — must stay empty


FIELD_LABELS = {"student_dob": "Date of birth", "student_gender": "Gender", "previous_school": "Previous school",
                "parent_email": "Parent email", "address": "Home address"}


def _client_ip(request: Request) -> str:
    """Right-most X-Forwarded-For hop is appended by our ingress and can't be forged by the client."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _validate_form(form: ApplicantForm, cfg: dict, options: dict) -> dict:
    data = form.model_dump(exclude={"website"})
    errors = []
    if not MOBILE_RX.match(data["parent_mobile"]):
        errors.append("Parent mobile: enter a valid phone number")
    if data.get("parent_email") and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", data["parent_email"]):
        errors.append("Parent email: enter a valid email")
    if options["classes"] and data["class_requested"] not in options["classes"]:
        errors.append("Class: choose one of the offered classes")
    if options["academic_years"] and data["academic_year"] not in options["academic_years"]:
        errors.append("Academic year: choose one of the offered years")
    for key, rule in cfg["fields"].items():
        if not rule.get("enabled", True):
            data[key] = None
        elif rule.get("required") and not (data.get(key) or "").strip():
            errors.append(f"{FIELD_LABELS.get(key, key)}: required")
    answers = {}
    for q in cfg.get("custom_questions", []):
        v = str(data["form_answers"].get(q["key"]) or "").strip()[:2000]
        if q.get("required") and not v:
            errors.append(f"{q['label']}: required")
        if q["type"] == "select" and v and v not in q.get("options", []):
            errors.append(f"{q['label']}: choose a listed option")
        if v: answers[q["key"]] = v
    data["form_answers"] = answers
    if errors:
        raise HTTPException(status_code=422, detail={"code": "invalid_application", "message": "; ".join(errors), "errors": errors})
    return data


async def _tenant_by_slug(db, slug: str) -> dict:
    t = await db.tenants.find_one({"slug": slug.lower()})
    if not t or t.get("status") in {"suspended", "archived", "deleted"}:
        raise HTTPException(status_code=404, detail="School not found")
    return t


async def _resolve_token(db, token: str) -> tuple[dict, dict]:
    link = await db.admission_links.find_one({"token_hash": _hash(token)})
    if not link or link["status"] != "active":
        raise HTTPException(status_code=404, detail={"code": "link_invalid", "message": "This application link is invalid or has been replaced"})
    if link["expires_at"] < _now().isoformat():
        raise HTTPException(status_code=410, detail={"code": "link_expired", "message": "This application link has expired — please ask the school for a new one"})
    app = await db.admission_applications.find_one({"_id": ObjectId(link["application_id"]), "tenant_id": link["tenant_id"]})
    if not app or app["status"] not in UPLOADABLE:
        raise HTTPException(status_code=410, detail={"code": "application_closed", "message": "This application is no longer open for changes"})
    await db.admission_links.update_one({"_id": link["_id"]}, {"$set": {"last_used_at": _now().isoformat()}})
    return link, app


# ============================================================
# Public: school form
# ============================================================
@public_router.get("/schools/{slug}/form")
async def public_form(slug: str):
    db = get_db()
    t = await _tenant_by_slug(db, slug)
    tid = str(t["_id"])
    settings = await _ensure_settings(tid)
    cfg = _form_config(settings)
    if not cfg.get("enabled", True):
        raise HTTPException(status_code=404, detail={"code": "form_disabled", "message": "Online admissions are not open for this school"})
    return {"school": {"name": t.get("name"), "slug": t.get("slug")},
            "intro_text": cfg.get("intro_text"), "fields": cfg["fields"], "custom_questions": cfg["custom_questions"],
            "options": await _form_options(db, tid, cfg), "document_types": _doc_types(settings)}


@public_router.post("/schools/{slug}/apply", status_code=201)
async def public_apply(slug: str, payload: ApplicantForm, request: Request):
    db = get_db()
    t = await _tenant_by_slug(db, slug)
    tid = str(t["_id"])
    settings = await _ensure_settings(tid)
    cfg = _form_config(settings)
    if not cfg.get("enabled", True):
        raise HTTPException(status_code=404, detail={"code": "form_disabled", "message": "Online admissions are not open for this school"})
    if payload.website:
        raise HTTPException(status_code=400, detail="Invalid submission")
    ip = _client_ip(request)
    since = (_now() - timedelta(hours=1)).isoformat()
    if await db.public_form_submissions.count_documents({"tenant_id": tid, "ip": ip, "at": {"$gte": since}}) >= PUBLIC_SUBMITS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many applications from this network — please try again later")
    data = _validate_form(payload, cfg, await _form_options(db, tid, cfg))
    now = _now().isoformat()
    lead = CrmLead(
        tenant_id=tid, inquiry_number=await next_number(tid, "INQ"),
        student_first_name=data["student_first_name"], student_last_name=data["student_last_name"],
        student_dob=data.get("student_dob"), student_gender=data.get("student_gender"),
        class_seeking=data["class_requested"], academic_year=data["academic_year"],
        previous_school=data.get("previous_school"), parent_name=data["parent_name"],
        parent_relationship=data["parent_relationship"], parent_mobile=data["parent_mobile"],
        parent_email=(data.get("parent_email") or None), source="website", inquiry_date=now,
        notes="Submitted via the online admission form",
    ).to_mongo()
    lead_res = await db.crm_leads.insert_one(lead)
    lead_id = str(lead_res.inserted_id)
    app = await create_application_record(db, tid, data, lead_id=lead_id, actor_id=None,
                                          app_number=await next_number(tid, "ADM"), status=APP_SUBMITTED,
                                          submitted_via="public_form")
    await db.public_form_submissions.insert_one({"tenant_id": tid, "ip": ip, "at": now, "application_id": str(app["_id"])})
    link = await _issue_link(db, tid, str(app["_id"]), lead_id, "public", cfg["link_expiry_days"], None)
    await log_event(action="admission.public.apply", resource="application", resource_id=str(app["_id"]), tenant_id=tid,
                    request=request, metadata={"lead_id": lead_id, "via": "public_form"})
    return {"application_number": app["application_number"], "token": link["token"],
            "url_path": link["url_path"], "expires_at": link["expires_at"]}


# ============================================================
# Public: token-scoped application
# ============================================================
async def _token_view(db, link: dict, app: dict) -> dict:
    tid = link["tenant_id"]
    settings = await _ensure_settings(tid)
    cfg = _form_config(settings)
    t = await db.tenants.find_one({"_id": ObjectId(tid)})
    req = {d["code"]: d for d in _doc_types(settings)}
    docs = await db.admission_documents.find({"tenant_id": tid, "application_id": str(app["_id"])}).sort("created_at", 1).to_list(100)
    keys = ["academic_year", "class_requested", "student_first_name", "student_last_name", "student_dob", "student_gender",
            "previous_school", "parent_name", "parent_relationship", "parent_mobile", "parent_email", "address", "form_answers"]
    return {
        "school": {"name": t.get("name"), "slug": t.get("slug")},
        "application_number": app["application_number"], "status": app["status"],
        "editable": app["status"] in EDITABLE, "can_upload": app["status"] in UPLOADABLE,
        "expires_at": link["expires_at"], "application": {k: app.get(k) for k in keys},
        "intro_text": cfg.get("intro_text"), "fields": cfg["fields"], "custom_questions": cfg["custom_questions"],
        "options": await _form_options(db, tid, cfg),
        "documents": [{"id": str(d["_id"]), "type_code": d["type_code"], "type_label": d["type_label"],
                       "requirement": req.get(d["type_code"], {}).get("requirement", "optional"),
                       "condition_note": req.get(d["type_code"], {}).get("condition_note"),
                       "status": d["status"], "filename": d.get("filename"),
                       "rejection_reason": d.get("rejection_reason")} for d in docs],
    }


@public_router.get("/t/{token}")
async def token_view(token: str):
    db = get_db()
    link, app = await _resolve_token(db, token)
    return await _token_view(db, link, app)


@public_router.put("/t/{token}")
async def token_update(token: str, payload: ApplicantForm, request: Request):
    db = get_db()
    link, app = await _resolve_token(db, token)
    if app["status"] not in EDITABLE:
        raise HTTPException(status_code=409, detail={"code": "not_editable", "message": "Details can no longer be changed — the school is reviewing your application"})
    if payload.website:
        raise HTTPException(status_code=400, detail="Invalid submission")
    tid = link["tenant_id"]
    cfg = _form_config(await _ensure_settings(tid))
    data = _validate_form(payload, cfg, await _form_options(db, tid, cfg))
    if data.get("parent_email"): data["parent_email"] = data["parent_email"].lower()
    data["updated_at"] = _now().isoformat()
    await db.admission_applications.update_one({"_id": app["_id"]}, {"$set": data})
    await log_event(action="admission.applicant.update", resource="application", resource_id=str(app["_id"]),
                    tenant_id=tid, request=request, metadata={"via": "applicant_link"})
    return await _token_view(db, link, await db.admission_applications.find_one({"_id": app["_id"]}))


@public_router.post("/t/{token}/submit")
async def token_submit(token: str, request: Request):
    db = get_db()
    link, app = await _resolve_token(db, token)
    tid = link["tenant_id"]
    nxt = {APP_DRAFT: APP_SUBMITTED, APP_DOCUMENTS_PENDING: APP_UNDER_REVIEW}.get(app["status"])
    if not nxt:
        raise HTTPException(status_code=409, detail={"code": "already_submitted", "message": "This application has already been submitted"})
    if not (app.get("academic_year") and app.get("class_requested")):
        raise HTTPException(status_code=422, detail={"code": "invalid_application", "message": "Save the form with academic year and class before submitting"})
    now = _now().isoformat()
    updates = {"status": nxt, "updated_at": now}
    if nxt == APP_SUBMITTED: updates["submitted_at"] = now
    await db.admission_applications.update_one({"_id": app["_id"]}, {"$set": updates})
    settings = await _ensure_settings(tid)
    await sync_lead_from_application(db, tid, app, nxt, actor_id=None, fee_required=fee_required(settings),
                                     note="Submitted by applicant")
    await log_event(action="admission.applicant.submit", resource="application", resource_id=str(app["_id"]),
                    tenant_id=tid, request=request, old_value={"status": app["status"]}, new_value={"status": nxt})
    return await _token_view(db, link, await db.admission_applications.find_one({"_id": app["_id"]}))


@public_router.post("/t/{token}/documents", status_code=201)
async def token_upload(token: str, request: Request, type_code: str = Form(...), file: UploadFile = File(...)):
    db = get_db()
    link, app = await _resolve_token(db, token)
    tid = link["tenant_id"]; app_id = str(app["_id"])
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail="Only PDF, JPG, PNG, WEBP or Word files are accepted")
    existing = await db.admission_documents.find_one({"tenant_id": tid, "application_id": app_id, "type_code": type_code})
    if not existing:
        raise HTTPException(status_code=400, detail="Unknown document type")
    if existing["status"] == DOC_VERIFIED:
        raise HTTPException(status_code=409, detail={"code": "already_verified", "message": "This document is already verified by the school"})
    if existing.get("storage_key"):
        try: await storage.delete(tid, existing["storage_key"])
        except Exception: pass
    key = await storage.put(tid, str(existing["_id"]), content)
    now = _now().isoformat()
    await db.admission_documents.update_one({"_id": existing["_id"]}, {"$set": {
        "filename": (file.filename or "document")[:200], "content_type": file.content_type, "size_bytes": len(content),
        "storage_key": key, "status": DOC_PENDING, "uploaded_by": "applicant", "uploaded_at": now,
        "verified_by": None, "verified_at": None, "rejection_reason": None, "updated_at": now}})
    await log_event(action="admission.applicant.document_upload", resource="document", resource_id=str(existing["_id"]),
                    tenant_id=tid, request=request, metadata={"application_id": app_id, "type_code": type_code, "size": len(content)})
    return await _token_view(db, link, app)
