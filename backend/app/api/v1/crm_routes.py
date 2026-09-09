"""CRM routes — leads, activities, follow-ups, campus visits, config, dashboard.

All routes are tenant-scoped via the authenticated user's token.
"""
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.schemas_crm import (
    ActivityOut, AdmissionSettingsOut, AssignRequest, CreateActivityRequest,
    CreateFollowupRequest, CreateLeadRequest, CreateVisitRequest, DashboardResponse,
    DuplicateCheckResult, FollowupOut, LeadOut, PagedLeads, StageMoveRequest,
    UpdateFollowupRequest, UpdateLeadRequest, UpdateSettingsRequest, UpdateVisitRequest,
    VisitOut,
)
from app.core.db import get_db
from app.core.deps import require_permission
from app.core.permissions import (
    P_CRM_ACTIVITY_CREATE, P_CRM_ACTIVITY_VIEW, P_CRM_ASSIGN, P_CRM_CONFIG,
    P_CRM_CREATE, P_CRM_DELETE, P_CRM_STAGE_MANAGE, P_CRM_UPDATE, P_CRM_VIEW,
)
from app.models.admission import DEFAULT_DOC_TYPES
from app.models.crm import (
    ACTIVITY_TYPES, CampusVisit, CrmActivity, CrmLead, DEFAULT_PIPELINE,
    DEFAULT_SOURCES, Followup, PRIORITIES, STAGE_ADMITTED, STAGE_LOST, VISIT_STATUSES,
)
from app.services.audit_service import log_event
from app.services.numbering import next_number

router = APIRouter(prefix="/school/crm", tags=["crm"])


def _oid(v: str) -> ObjectId:
    try:
        return ObjectId(v)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Not found")


def _lead_out(d: dict) -> LeadOut:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return LeadOut(**d)


async def _ensure_settings(tenant_id: str) -> dict:
    db = get_db()
    s = await db.admission_settings.find_one({"tenant_id": tenant_id})
    if s:
        return s
    doc = {
        "tenant_id": tenant_id,
        "pipeline_stages": DEFAULT_PIPELINE,
        "sources": DEFAULT_SOURCES,
        "priorities": PRIORITIES,
        "doc_types": DEFAULT_DOC_TYPES,
        "require_docs_for_approval": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admission_settings.insert_one(doc)
    return doc


# ============================================================
# Settings / config
# ============================================================
@router.get("/settings", response_model=AdmissionSettingsOut)
async def get_settings(user: dict = Depends(require_permission(P_CRM_VIEW))):
    s = await _ensure_settings(user["tenant_id"])
    return AdmissionSettingsOut(
        pipeline_stages=s["pipeline_stages"], sources=s["sources"],
        priorities=s["priorities"], doc_types=s["doc_types"],
        require_docs_for_approval=s.get("require_docs_for_approval", True),
    )


@router.patch("/settings", response_model=AdmissionSettingsOut)
async def update_settings(
    payload: UpdateSettingsRequest, request: Request,
    user: dict = Depends(require_permission(P_CRM_CONFIG)),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    db = get_db()
    await _ensure_settings(user["tenant_id"])
    old = await db.admission_settings.find_one({"tenant_id": user["tenant_id"]})
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.admission_settings.update_one({"tenant_id": user["tenant_id"]}, {"$set": updates})
    new = await db.admission_settings.find_one({"tenant_id": user["tenant_id"]})
    await log_event(
        action="crm.settings.update", resource="admission_settings", resource_id=str(new["_id"]),
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={k: old.get(k) for k in updates.keys() if k != "updated_at"},
        new_value={k: v for k, v in updates.items() if k != "updated_at"},
    )
    return AdmissionSettingsOut(
        pipeline_stages=new["pipeline_stages"], sources=new["sources"],
        priorities=new["priorities"], doc_types=new["doc_types"],
        require_docs_for_approval=new.get("require_docs_for_approval", True),
    )


# ============================================================
# Duplicate detection
# ============================================================
@router.get("/leads/check-duplicate", response_model=DuplicateCheckResult)
async def check_duplicate(
    parent_mobile: str | None = None, parent_email: str | None = None,
    student_first_name: str | None = None, student_last_name: str | None = None,
    student_dob: str | None = None,
    user: dict = Depends(require_permission(P_CRM_VIEW)),
):
    or_clauses = []
    if parent_mobile:
        or_clauses.append({"parent_mobile": parent_mobile})
    if parent_email:
        or_clauses.append({"parent_email": parent_email.lower()})
    if student_first_name and student_last_name and student_dob:
        or_clauses.append({
            "student_first_name": {"$regex": f"^{student_first_name}$", "$options": "i"},
            "student_last_name": {"$regex": f"^{student_last_name}$", "$options": "i"},
            "student_dob": student_dob,
        })
    if not or_clauses:
        return DuplicateCheckResult(duplicates=[])
    q = {"tenant_id": user["tenant_id"], "$or": or_clauses}
    docs = await get_db().crm_leads.find(q).sort("created_at", -1).to_list(10)
    return DuplicateCheckResult(duplicates=[_lead_out(d) for d in docs])


# ============================================================
# Leads
# ============================================================
@router.post("/leads", response_model=LeadOut, status_code=201)
async def create_lead(
    payload: CreateLeadRequest, request: Request,
    user: dict = Depends(require_permission(P_CRM_CREATE)),
):
    db = get_db()
    if not payload.force and payload.student_dob:
        # A lead is a duplicate only when the *same student* (name + DOB)
        # is submitted with an overlapping contact.  Siblings that share only
        # a parent phone are legitimately allowed through.
        contact_or = [{"parent_mobile": payload.parent_mobile}]
        if payload.parent_email:
            contact_or.append({"parent_email": payload.parent_email.lower()})
        dup = await db.crm_leads.find_one({
            "tenant_id": user["tenant_id"],
            "$and": [
                {"$or": contact_or},
                {"student_first_name": {"$regex": f"^{payload.student_first_name}$", "$options": "i"}},
                {"student_last_name": {"$regex": f"^{payload.student_last_name}$", "$options": "i"}},
                {"student_dob": payload.student_dob},
            ],
        })
        if dup:
            raise HTTPException(status_code=409, detail={"code": "duplicate_lead", "existing_lead_id": str(dup["_id"]), "message": "Possible existing inquiry found"})

    inquiry_number = await next_number(user["tenant_id"], "INQ")
    now = datetime.now(timezone.utc).isoformat()
    lead = CrmLead(
        tenant_id=user["tenant_id"],
        inquiry_number=inquiry_number,
        student_first_name=payload.student_first_name,
        student_last_name=payload.student_last_name,
        student_dob=payload.student_dob,
        student_gender=payload.student_gender,
        class_seeking=payload.class_seeking,
        academic_year=payload.academic_year,
        previous_school=payload.previous_school,
        parent_name=payload.parent_name,
        parent_relationship=payload.parent_relationship,
        parent_mobile=payload.parent_mobile,
        parent_email=payload.parent_email.lower() if payload.parent_email else None,
        alt_contact=payload.alt_contact,
        source=payload.source, preferred_contact=payload.preferred_contact,
        assigned_to=payload.assigned_to, priority=payload.priority,
        notes=payload.notes, inquiry_date=payload.inquiry_date or now,
        last_activity_at=now,
    ).to_mongo()
    res = await db.crm_leads.insert_one(lead)
    lead["_id"] = res.inserted_id
    lead_id = str(res.inserted_id)

    # System activity — "inquiry created"
    await db.crm_activities.insert_one(CrmActivity(
        tenant_id=user["tenant_id"], lead_id=lead_id, activity_type="note",
        subject="Inquiry created", notes=f"Inquiry {inquiry_number} created",
        activity_at=now, user_id=user["id"], is_system=True,
    ).to_mongo())

    await log_event(
        action="crm.lead.create", resource="crm_lead", resource_id=lead_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        new_value={"inquiry_number": inquiry_number, "parent_mobile": payload.parent_mobile,
                   "class_seeking": payload.class_seeking},
    )
    return _lead_out(lead)


@router.get("/leads", response_model=PagedLeads)
async def list_leads(
    q: str | None = None, stage: str | None = None, source: str | None = None,
    priority: str | None = None, academic_year: str | None = None,
    class_seeking: str | None = None, assigned_to: str | None = None,
    date_from: str | None = None, date_to: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    sort: str = Query("created_at:desc"),
    user: dict = Depends(require_permission(P_CRM_VIEW)),
):
    query: dict = {"tenant_id": user["tenant_id"]}
    if stage:
        query["stage"] = stage
    if source:
        query["source"] = source
    if priority:
        query["priority"] = priority
    if academic_year:
        query["academic_year"] = academic_year
    if class_seeking:
        query["class_seeking"] = class_seeking
    if assigned_to:
        query["assigned_to"] = assigned_to
    if date_from or date_to:
        query["created_at"] = {}
        if date_from:
            query["created_at"]["$gte"] = date_from
        if date_to:
            query["created_at"]["$lte"] = date_to
    if q:
        rx = {"$regex": q, "$options": "i"}
        query["$or"] = [
            {"student_first_name": rx}, {"student_last_name": rx},
            {"parent_name": rx}, {"parent_mobile": rx}, {"parent_email": rx},
            {"inquiry_number": rx},
        ]

    field, _, direction = sort.partition(":")
    sort_dir = -1 if direction != "asc" else 1
    if field not in {"created_at", "updated_at", "inquiry_number", "priority", "stage", "next_followup_at"}:
        field = "created_at"

    db = get_db()
    total = await db.crm_leads.count_documents(query)
    cursor = db.crm_leads.find(query).sort(field, sort_dir).skip((page - 1) * page_size).limit(page_size)
    docs = await cursor.to_list(page_size)
    return PagedLeads(items=[_lead_out(d) for d in docs], total=total, page=page, page_size=page_size)


@router.get("/leads/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: str, user: dict = Depends(require_permission(P_CRM_VIEW))):
    d = await get_db().crm_leads.find_one({"_id": _oid(lead_id), "tenant_id": user["tenant_id"]})
    if not d:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _lead_out(d)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: str, payload: UpdateLeadRequest, request: Request,
    user: dict = Depends(require_permission(P_CRM_UPDATE)),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if updates.get("parent_email"):
        updates["parent_email"] = updates["parent_email"].lower()
    db = get_db()
    old = await db.crm_leads.find_one({"_id": _oid(lead_id), "tenant_id": user["tenant_id"]})
    if not old:
        raise HTTPException(status_code=404, detail="Lead not found")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.crm_leads.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.crm_leads.find_one({"_id": old["_id"]})
    await log_event(
        action="crm.lead.update", resource="crm_lead", resource_id=lead_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={k: old.get(k) for k in updates.keys() if k != "updated_at"},
        new_value={k: v for k, v in updates.items() if k != "updated_at"},
    )
    return _lead_out(new)


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, request: Request, user: dict = Depends(require_permission(P_CRM_DELETE))):
    db = get_db()
    old = await db.crm_leads.find_one({"_id": _oid(lead_id), "tenant_id": user["tenant_id"]})
    if not old:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.crm_leads.delete_one({"_id": old["_id"]})
    await log_event(
        action="crm.lead.delete", resource="crm_lead", resource_id=lead_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={"inquiry_number": old.get("inquiry_number")},
    )
    return {"ok": True}


@router.post("/leads/{lead_id}/assign", response_model=LeadOut)
async def assign_lead(
    lead_id: str, payload: AssignRequest, request: Request,
    user: dict = Depends(require_permission(P_CRM_ASSIGN)),
):
    db = get_db()
    old = await db.crm_leads.find_one({"_id": _oid(lead_id), "tenant_id": user["tenant_id"]})
    if not old:
        raise HTTPException(status_code=404, detail="Lead not found")
    # Verify the target user exists in the same tenant
    target = await db.users.find_one({"_id": _oid(payload.assigned_to), "tenant_id": user["tenant_id"]})
    if not target:
        raise HTTPException(status_code=400, detail="Target user not in this school")
    await db.crm_leads.update_one({"_id": old["_id"]}, {"$set": {
        "assigned_to": payload.assigned_to,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }})
    new = await db.crm_leads.find_one({"_id": old["_id"]})
    await log_event(
        action="crm.lead.assign", resource="crm_lead", resource_id=lead_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={"assigned_to": old.get("assigned_to")},
        new_value={"assigned_to": payload.assigned_to},
    )
    return _lead_out(new)


@router.post("/leads/{lead_id}/stage", response_model=LeadOut)
async def move_stage(
    lead_id: str, payload: StageMoveRequest, request: Request,
    user: dict = Depends(require_permission(P_CRM_STAGE_MANAGE)),
):
    settings = await _ensure_settings(user["tenant_id"])
    codes = [s["code"] for s in settings["pipeline_stages"]]
    if payload.stage not in codes:
        raise HTTPException(status_code=400, detail=f"Unknown stage. Allowed: {codes}")

    db = get_db()
    old = await db.crm_leads.find_one({"_id": _oid(lead_id), "tenant_id": user["tenant_id"]})
    if not old:
        raise HTTPException(status_code=404, detail="Lead not found")

    updates = {
        "stage": payload.stage,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.stage == STAGE_LOST and payload.reason:
        updates["lost_reason"] = payload.reason
    if payload.stage == STAGE_ADMITTED and not old.get("converted_at"):
        # Marking a stage as ADMITTED does NOT itself create a Student — conversion service does that.
        pass

    await db.crm_leads.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.crm_leads.find_one({"_id": old["_id"]})

    # Timeline entry
    await db.crm_activities.insert_one(CrmActivity(
        tenant_id=user["tenant_id"], lead_id=lead_id, activity_type="note", is_system=True,
        subject=f"Stage → {payload.stage}", notes=payload.reason,
        activity_at=updates["updated_at"], user_id=user["id"],
    ).to_mongo())

    await log_event(
        action="crm.lead.stage", resource="crm_lead", resource_id=lead_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={"stage": old.get("stage")}, new_value={"stage": payload.stage},
        metadata={"reason": payload.reason},
    )
    return _lead_out(new)


# ============================================================
# Activities
# ============================================================
@router.post("/leads/{lead_id}/activities", response_model=ActivityOut, status_code=201)
async def create_activity(
    lead_id: str, payload: CreateActivityRequest, request: Request,
    user: dict = Depends(require_permission(P_CRM_ACTIVITY_CREATE)),
):
    if payload.activity_type not in ACTIVITY_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid activity type. Allowed: {ACTIVITY_TYPES}")
    db = get_db()
    lead = await db.crm_leads.find_one({"_id": _oid(lead_id), "tenant_id": user["tenant_id"]})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    now = datetime.now(timezone.utc).isoformat()
    act = CrmActivity(
        tenant_id=user["tenant_id"], lead_id=lead_id,
        activity_type=payload.activity_type, subject=payload.subject,
        outcome=payload.outcome, notes=payload.notes,
        activity_at=payload.activity_at or now, user_id=user["id"],
        next_action=payload.next_action, next_followup_at=payload.next_followup_at,
    ).to_mongo()
    res = await db.crm_activities.insert_one(act)
    act["id"] = str(res.inserted_id); act.pop("_id", None)

    lead_updates = {"last_activity_at": now, "updated_at": now}
    if payload.next_followup_at:
        lead_updates["next_followup_at"] = payload.next_followup_at
    await db.crm_leads.update_one({"_id": _oid(lead_id)}, {"$set": lead_updates})

    if payload.next_followup_at:
        await db.followups.insert_one(Followup(
            tenant_id=user["tenant_id"], lead_id=lead_id,
            due_at=payload.next_followup_at, title=payload.next_action or "Follow-up",
            channel=payload.activity_type if payload.activity_type in {"phone_call","whatsapp","sms","email","meeting"} else "phone_call",
            assigned_to=lead.get("assigned_to") or user["id"],
        ).to_mongo())

    await log_event(
        action="crm.activity.create", resource="crm_activity", resource_id=act["id"],
        tenant_id=user["tenant_id"], actor=user, request=request,
        metadata={"lead_id": lead_id, "activity_type": payload.activity_type},
    )
    return ActivityOut(**act)


@router.get("/leads/{lead_id}/activities", response_model=list[ActivityOut])
async def list_activities(lead_id: str, user: dict = Depends(require_permission(P_CRM_ACTIVITY_VIEW))):
    db = get_db()
    if not await db.crm_leads.find_one({"_id": _oid(lead_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Lead not found")
    docs = await db.crm_activities.find({"tenant_id": user["tenant_id"], "lead_id": lead_id}).sort("created_at", -1).to_list(500)
    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        out.append(ActivityOut(**d))
    return out


# ============================================================
# Follow-ups
# ============================================================
@router.post("/leads/{lead_id}/followups", response_model=FollowupOut, status_code=201)
async def create_followup(
    lead_id: str, payload: CreateFollowupRequest, request: Request,
    user: dict = Depends(require_permission(P_CRM_ACTIVITY_CREATE)),
):
    db = get_db()
    lead = await db.crm_leads.find_one({"_id": _oid(lead_id), "tenant_id": user["tenant_id"]})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    doc = Followup(
        tenant_id=user["tenant_id"], lead_id=lead_id, due_at=payload.due_at,
        title=payload.title, channel=payload.channel, notes=payload.notes,
        assigned_to=payload.assigned_to or lead.get("assigned_to") or user["id"],
    ).to_mongo()
    res = await db.followups.insert_one(doc)
    doc["id"] = str(res.inserted_id); doc.pop("_id", None)
    await db.crm_leads.update_one({"_id": _oid(lead_id)}, {"$set": {"next_followup_at": payload.due_at}})
    await log_event(
        action="crm.followup.create", resource="followup", resource_id=doc["id"],
        tenant_id=user["tenant_id"], actor=user, request=request,
        metadata={"lead_id": lead_id, "due_at": payload.due_at},
    )
    return FollowupOut(**doc)


@router.get("/followups", response_model=list[FollowupOut])
async def list_followups(
    status: str | None = None, bucket: str | None = None,
    assigned_to: str | None = None, lead_id: str | None = None,
    user: dict = Depends(require_permission(P_CRM_ACTIVITY_VIEW)),
):
    query: dict = {"tenant_id": user["tenant_id"]}
    if status:
        query["status"] = status
    if assigned_to:
        query["assigned_to"] = assigned_to
    if lead_id:
        query["lead_id"] = lead_id
    now = datetime.now(timezone.utc)
    if bucket:
        query["status"] = "pending"
        start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end = (now.replace(hour=23, minute=59, second=59, microsecond=0)).isoformat()
        if bucket == "today":
            query["due_at"] = {"$gte": start, "$lte": end}
        elif bucket == "overdue":
            query["due_at"] = {"$lt": start}
        elif bucket == "upcoming":
            query["due_at"] = {"$gt": end}
    docs = await get_db().followups.find(query).sort("due_at", 1).to_list(500)
    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        out.append(FollowupOut(**d))
    return out


@router.patch("/followups/{followup_id}", response_model=FollowupOut)
async def update_followup(
    followup_id: str, payload: UpdateFollowupRequest, request: Request,
    user: dict = Depends(require_permission(P_CRM_ACTIVITY_CREATE)),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    db = get_db()
    old = await db.followups.find_one({"_id": _oid(followup_id), "tenant_id": user["tenant_id"]})
    if not old:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    now = datetime.now(timezone.utc).isoformat()
    updates["updated_at"] = now
    if updates.get("status") == "completed":
        updates["completed_at"] = now
        updates["completed_by"] = user["id"]
    await db.followups.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.followups.find_one({"_id": old["_id"]})
    new["id"] = str(new.pop("_id"))
    await log_event(
        action="crm.followup.update", resource="followup", resource_id=followup_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={k: old.get(k) for k in updates.keys() if k not in {"updated_at","completed_at","completed_by"}},
        new_value={k: v for k, v in updates.items() if k not in {"updated_at","completed_at","completed_by"}},
    )
    return FollowupOut(**new)


# ============================================================
# Campus visits
# ============================================================
@router.post("/visits", response_model=VisitOut, status_code=201)
async def create_visit(
    payload: CreateVisitRequest, request: Request,
    user: dict = Depends(require_permission(P_CRM_ACTIVITY_CREATE)),
):
    db = get_db()
    lead = await db.crm_leads.find_one({"_id": _oid(payload.lead_id), "tenant_id": user["tenant_id"]})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Simple double-booking guard: same staff, same day, overlapping time window.
    if payload.assigned_staff_id:
        clash = await db.campus_visits.find_one({
            "tenant_id": user["tenant_id"],
            "assigned_staff_id": payload.assigned_staff_id,
            "scheduled_date": payload.scheduled_date,
            "status": {"$nin": ["cancelled", "no_show"]},
            "start_time": {"$lt": payload.end_time},
            "end_time": {"$gt": payload.start_time},
        })
        if clash:
            raise HTTPException(status_code=409, detail="Selected staff is already booked in that slot")

    doc = CampusVisit(
        tenant_id=user["tenant_id"], lead_id=payload.lead_id,
        scheduled_date=payload.scheduled_date, start_time=payload.start_time,
        end_time=payload.end_time, expected_visitors=payload.expected_visitors,
        assigned_staff_id=payload.assigned_staff_id, purpose=payload.purpose,
        notes=payload.notes,
    ).to_mongo()
    res = await db.campus_visits.insert_one(doc)
    doc["id"] = str(res.inserted_id); doc.pop("_id", None)

    # Move lead into VISIT_SCHEDULED if it's still earlier in the funnel
    settings = await _ensure_settings(user["tenant_id"])
    order = {s["code"]: s["order"] for s in settings["pipeline_stages"]}
    current_order = order.get(lead.get("stage"), 0)
    visit_order = order.get("VISIT_SCHEDULED", 3)
    if current_order < visit_order:
        await db.crm_leads.update_one({"_id": _oid(payload.lead_id)}, {"$set": {"stage": "VISIT_SCHEDULED"}})

    await log_event(
        action="crm.visit.create", resource="campus_visit", resource_id=doc["id"],
        tenant_id=user["tenant_id"], actor=user, request=request,
        metadata={"lead_id": payload.lead_id, "date": payload.scheduled_date},
    )
    return VisitOut(**doc)


@router.get("/visits", response_model=list[VisitOut])
async def list_visits(
    date_from: str | None = None, date_to: str | None = None,
    status: str | None = None, staff_id: str | None = None,
    user: dict = Depends(require_permission(P_CRM_VIEW)),
):
    query: dict = {"tenant_id": user["tenant_id"]}
    if status:
        if status not in VISIT_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {VISIT_STATUSES}")
        query["status"] = status
    if staff_id:
        query["assigned_staff_id"] = staff_id
    if date_from or date_to:
        query["scheduled_date"] = {}
        if date_from:
            query["scheduled_date"]["$gte"] = date_from
        if date_to:
            query["scheduled_date"]["$lte"] = date_to
    docs = await get_db().campus_visits.find(query).sort("scheduled_date", 1).to_list(500)
    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        out.append(VisitOut(**d))
    return out


@router.patch("/visits/{visit_id}", response_model=VisitOut)
async def update_visit(
    visit_id: str, payload: UpdateVisitRequest, request: Request,
    user: dict = Depends(require_permission(P_CRM_UPDATE)),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if updates.get("status") and updates["status"] not in VISIT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {VISIT_STATUSES}")
    db = get_db()
    old = await db.campus_visits.find_one({"_id": _oid(visit_id), "tenant_id": user["tenant_id"]})
    if not old:
        raise HTTPException(status_code=404, detail="Visit not found")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.campus_visits.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.campus_visits.find_one({"_id": old["_id"]})
    new["id"] = str(new.pop("_id"))
    await log_event(
        action="crm.visit.update", resource="campus_visit", resource_id=visit_id,
        tenant_id=user["tenant_id"], actor=user, request=request,
        old_value={k: old.get(k) for k in updates.keys() if k != "updated_at"},
        new_value={k: v for k, v in updates.items() if k != "updated_at"},
    )
    return VisitOut(**new)


# ============================================================
# Dashboard
# ============================================================
@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    academic_year: str | None = None, class_seeking: str | None = None,
    source: str | None = None, assigned_to: str | None = None,
    date_from: str | None = None, date_to: str | None = None,
    user: dict = Depends(require_permission(P_CRM_VIEW)),
):
    db = get_db()
    base: dict = {"tenant_id": user["tenant_id"]}
    if academic_year:
        base["academic_year"] = academic_year
    if class_seeking:
        base["class_seeking"] = class_seeking
    if source:
        base["source"] = source
    if assigned_to:
        base["assigned_to"] = assigned_to
    if date_from or date_to:
        base["created_at"] = {}
        if date_from:
            base["created_at"]["$gte"] = date_from
        if date_to:
            base["created_at"]["$lte"] = date_to

    total_inquiries = await db.crm_leads.count_documents(base)

    now = datetime.now(timezone.utc)
    seven_days = (now - timedelta(days=7)).isoformat()
    q_new = dict(base)
    q_new.setdefault("created_at", {})
    if isinstance(q_new["created_at"], dict):
        q_new["created_at"] = {**q_new["created_at"], "$gte": seven_days}
    else:
        q_new["created_at"] = {"$gte": seven_days}
    new_inquiries_7d = await db.crm_leads.count_documents(q_new)

    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    followups_due_today = await db.followups.count_documents({
        "tenant_id": user["tenant_id"], "status": "pending",
        "due_at": {"$gte": start_of_day, "$lte": end_of_day},
    })
    overdue_followups = await db.followups.count_documents({
        "tenant_id": user["tenant_id"], "status": "pending", "due_at": {"$lt": start_of_day},
    })
    seven_forward = (now + timedelta(days=7)).isoformat()
    upcoming_visits_7d = await db.campus_visits.count_documents({
        "tenant_id": user["tenant_id"],
        "scheduled_date": {"$gte": now.strftime("%Y-%m-%d"), "$lte": seven_forward[:10]},
        "status": {"$in": ["scheduled", "confirmed"]},
    })

    apps_base = {"tenant_id": user["tenant_id"]}
    apps_in_progress = await db.admission_applications.count_documents({
        **apps_base, "status": {"$in": ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "DOCUMENTS_PENDING"]},
    })
    apps_pending_review = await db.admission_applications.count_documents({
        **apps_base, "status": {"$in": ["SUBMITTED", "UNDER_REVIEW"]},
    })
    apps_approved = await db.admission_applications.count_documents({**apps_base, "status": "APPROVED"})
    admissions_confirmed = await db.admission_applications.count_documents({**apps_base, "status": "CONVERTED"})

    lost = await db.crm_leads.count_documents({**base, "stage": "LOST"})
    admitted = await db.crm_leads.count_documents({**base, "stage": "ADMITTED"})
    conversion_rate = (admitted / total_inquiries * 100) if total_inquiries else 0.0

    stage_counts: dict = {}
    async for row in db.crm_leads.aggregate([{"$match": base}, {"$group": {"_id": "$stage", "n": {"$sum": 1}}}]):
        stage_counts[row["_id"]] = row["n"]

    source_counts: dict = {}
    async for row in db.crm_leads.aggregate([{"$match": base}, {"$group": {"_id": "$source", "n": {"$sum": 1}}}]):
        source_counts[row["_id"] or "unknown"] = row["n"]

    class_counts: dict = {}
    async for row in db.crm_leads.aggregate([{"$match": base}, {"$group": {"_id": "$class_seeking", "n": {"$sum": 1}}}]):
        class_counts[row["_id"] or "—"] = row["n"]

    return DashboardResponse(
        total_inquiries=total_inquiries,
        new_inquiries_7d=new_inquiries_7d,
        followups_due_today=followups_due_today,
        overdue_followups=overdue_followups,
        upcoming_visits_7d=upcoming_visits_7d,
        applications_in_progress=apps_in_progress,
        applications_pending_review=apps_pending_review,
        applications_approved=apps_approved,
        admissions_confirmed=admissions_confirmed,
        lost_or_rejected=lost,
        conversion_rate=round(conversion_rate, 2),
        stage_counts=stage_counts, source_counts=source_counts, class_counts=class_counts,
    )
