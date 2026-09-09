"""Student Master + Guardian + Family + Enrollment routes."""
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field

from app.core.db import get_db
from app.core.deps import require_permission
from app.core.permissions import (
    P_FAMILY_MANAGE, P_FAMILY_VIEW, P_GUARDIAN_CREATE, P_GUARDIAN_UPDATE,
    P_GUARDIAN_VIEW, P_STUDENT_CREATE, P_STUDENT_DOC_UPLOAD, P_STUDENT_DOC_VIEW,
    P_STUDENT_ENROLL_MANAGE, P_STUDENT_ENROLL_VIEW, P_STUDENT_FAMILY_MANAGE,
    P_STUDENT_GUARDIAN_MANAGE, P_STUDENT_GUARDIAN_VIEW, P_STUDENT_STATUS_MANAGE,
    P_STUDENT_UPDATE, P_STUDENT_VIEW,
)
from app.models.student import LIFECYCLE_STATES, Family, Guardian, Student, StudentEnrollment, StudentGuardian
from app.services.audit_service import log_event
from app.services.numbering import next_number

router = APIRouter(prefix="/school", tags=["students"])


def _oid(v: str) -> ObjectId:
    try: return ObjectId(v)
    except InvalidId: raise HTTPException(status_code=404, detail="Not found")


def _out(d: dict) -> dict:
    d = dict(d); d["id"] = str(d.pop("_id")); return d


# -------- Schemas ----------
class CreateStudent(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    middle_name: str | None = None
    last_name: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    academic_year: str | None = None
    class_name: str | None = None
    section: str | None = None
    roll_number: str | None = None
    residential_address: dict | None = None
    force: bool = False


class UpdateStudent(BaseModel):
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    preferred_name: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    blood_group: str | None = None
    nationality: str | None = None
    mother_tongue: str | None = None
    category: str | None = None
    profile_photo_url: str | None = None
    academic_year: str | None = None
    class_name: str | None = None
    section: str | None = None
    roll_number: str | None = None
    house: str | None = None
    residential_address: dict | None = None
    permanent_address: dict | None = None
    family_id: str | None = None


class StatusChange(BaseModel):
    status: str
    reason: str | None = None
    effective_date: str | None = None


class CreateGuardian(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    middle_name: str | None = None
    last_name: str | None = None
    relationship_type: str = "guardian"
    mobile_primary: str = Field(min_length=4, max_length=32)
    mobile_secondary: str | None = None
    email: EmailStr | None = None
    occupation: str | None = None
    employer: str | None = None
    address: dict | None = None
    emergency_contact_flag: bool = False
    family_id: str | None = None


class UpdateGuardian(BaseModel):
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    relationship_type: str | None = None
    mobile_primary: str | None = None
    mobile_secondary: str | None = None
    email: EmailStr | None = None
    occupation: str | None = None
    employer: str | None = None
    address: dict | None = None
    emergency_contact_flag: bool | None = None
    status: str | None = None
    family_id: str | None = None


class LinkGuardian(BaseModel):
    guardian_id: str
    relationship_type: str = "guardian"
    is_primary: bool = False
    is_emergency_contact: bool = False
    has_pickup_authorization: bool = False
    has_fee_responsibility: bool = False
    has_academic_access: bool = True
    communication_priority: int = 1


class UpdateRelationship(BaseModel):
    relationship_type: str | None = None
    is_primary: bool | None = None
    is_emergency_contact: bool | None = None
    has_pickup_authorization: bool | None = None
    has_fee_responsibility: bool | None = None
    has_academic_access: bool | None = None
    communication_priority: int | None = None


class CreateEnrollment(BaseModel):
    academic_year: str
    class_name: str
    section: str | None = None
    roll_number: str | None = None
    house: str | None = None
    start_date: str | None = None
    remarks: str | None = None


class UpdateEnrollment(BaseModel):
    class_name: str | None = None
    section: str | None = None
    roll_number: str | None = None
    house: str | None = None
    enrollment_status: str | None = None
    end_date: str | None = None
    promotion_status: str | None = None
    remarks: str | None = None


class CreateFamily(BaseModel):
    family_name: str = Field(min_length=1, max_length=120)
    primary_contact_guardian_id: str | None = None
    address: dict | None = None
    notes: str | None = None


class UpdateFamily(BaseModel):
    family_name: str | None = None
    primary_contact_guardian_id: str | None = None
    address: dict | None = None
    notes: str | None = None
    communication_preferences: dict | None = None


# ============================================================
# Students
# ============================================================
@router.post("/students", status_code=201)
async def create_student(payload: CreateStudent, request: Request, user: dict = Depends(require_permission(P_STUDENT_CREATE))):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    if not payload.force and payload.date_of_birth:
        dup = await db.students.find_one({
            "tenant_id": user["tenant_id"],
            "first_name": {"$regex": f"^{re.escape(payload.first_name)}$", "$options": "i"},
            "last_name": {"$regex": f"^{re.escape(payload.last_name or '')}$", "$options": "i"},
            "date_of_birth": payload.date_of_birth,
        })
        if dup:
            raise HTTPException(status_code=409, detail={"code": "duplicate_student", "existing_student_id": str(dup["_id"]), "message": "Possible existing student"})
    admission_number = await next_number(user["tenant_id"], "STU", width=6)
    doc = Student(
        tenant_id=user["tenant_id"], admission_number=admission_number,
        first_name=payload.first_name, middle_name=payload.middle_name,
        last_name=payload.last_name, date_of_birth=payload.date_of_birth,
        gender=payload.gender, academic_year=payload.academic_year,
        class_name=payload.class_name, section=payload.section,
        roll_number=payload.roll_number, residential_address=payload.residential_address,
        status="ACTIVE", status_effective_date=now, admission_date=now,
    ).to_mongo()
    res = await db.students.insert_one(doc)
    doc["_id"] = res.inserted_id
    await log_event(action="student.create", resource="student", resource_id=str(res.inserted_id),
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    new_value={"admission_number": admission_number})
    return _out(doc)


@router.get("/students/stats")
async def student_stats(
    academic_year: str | None = None,
    user: dict = Depends(require_permission(P_STUDENT_VIEW)),
):
    """KPIs for the Student Master list header.

    Returns totals, currently-active count, new-this-year count (based on
    ``academic_year`` snapshot), and a "missing info" bucket (no DOB OR no
    active guardian link) — useful for admissions follow-up.
    """
    db = get_db()
    tid = user["tenant_id"]
    base = {"tenant_id": tid}
    total = await db.students.count_documents(base)
    active = await db.students.count_documents({**base, "status": "ACTIVE"})
    new_this_year = 0
    if academic_year:
        new_this_year = await db.students.count_documents({**base, "academic_year": academic_year})
    # "Missing info" bucket — a student with either no DOB OR no active guardian.
    # We compute the *union* to avoid double-counting students missing both.
    linked_ids = await db.student_guardians.distinct(
        "student_id", {"tenant_id": tid, "end_date": None}
    )
    linked_oids = set()
    for x in linked_ids:
        try: linked_oids.add(ObjectId(x))
        except Exception: pass
    missing_dob_ids = set(await db.students.distinct("_id", {**base, "$or": [{"date_of_birth": None}, {"date_of_birth": ""}]}))
    all_ids = set(await db.students.distinct("_id", base))
    missing_guardian_ids = all_ids - linked_oids
    missing_info_ids = missing_dob_ids | missing_guardian_ids
    return {
        "total": total, "active": active,
        "new_this_year": new_this_year,
        "missing_info": len(missing_info_ids),
        "missing_dob": len(missing_dob_ids),
        "missing_guardians": len(missing_guardian_ids),
    }


@router.get("/students/{sid}/timeline")
async def student_timeline(
    sid: str, limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(require_permission(P_STUDENT_VIEW)),
):
    db = get_db()
    if not await db.students.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Student not found")
    # Direct student events + enrollment/guardian-link events that reference the student.
    enroll_ids = [str(d["_id"]) for d in await db.student_enrollments.find(
        {"tenant_id": user["tenant_id"], "student_id": sid}, {"_id": 1}
    ).to_list(200)]
    sg_ids = [str(d["_id"]) for d in await db.student_guardians.find(
        {"tenant_id": user["tenant_id"], "student_id": sid}, {"_id": 1}
    ).to_list(200)]
    query = {
        "tenant_id": user["tenant_id"],
        "$or": [
            {"resource": "student", "resource_id": sid},
            {"resource": "student_enrollment", "resource_id": {"$in": enroll_ids}},
            {"resource": "student_guardian", "resource_id": {"$in": sg_ids}},
        ],
    }
    docs = await db.audit_logs.find(query).sort("created_at", -1).to_list(limit)
    return [{
        "id": str(d["_id"]), "action": d["action"], "resource": d["resource"],
        "resource_id": d.get("resource_id"), "actor_email": d.get("actor_email"),
        "created_at": d["created_at"], "metadata": d.get("metadata"),
    } for d in docs]


@router.get("/students")
async def list_students(
    q: str | None = None, status: str | None = None, academic_year: str | None = None,
    class_name: str | None = None, section: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    user: dict = Depends(require_permission(P_STUDENT_VIEW)),
):
    query: dict = {"tenant_id": user["tenant_id"]}
    if status: query["status"] = status
    if academic_year: query["academic_year"] = academic_year
    if class_name: query["class_name"] = class_name
    if section: query["section"] = section
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [{"first_name": rx}, {"last_name": rx},
                        {"admission_number": rx}, {"roll_number": rx}]
    db = get_db()
    total = await db.students.count_documents(query)
    docs = await db.students.find(query).sort("created_at", -1).skip((page-1)*page_size).limit(page_size).to_list(page_size)
    return {"items": [_out(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.get("/students/{sid}")
async def get_student(sid: str, user: dict = Depends(require_permission(P_STUDENT_VIEW))):
    d = await get_db().students.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]})
    if not d: raise HTTPException(status_code=404, detail="Student not found")
    return _out(d)


@router.patch("/students/{sid}")
async def update_student(sid: str, payload: UpdateStudent, request: Request, user: dict = Depends(require_permission(P_STUDENT_UPDATE))):
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    db = get_db()
    old = await db.students.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Student not found")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.students.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.students.find_one({"_id": old["_id"]})
    await log_event(action="student.update", resource="student", resource_id=sid,
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(new)


@router.post("/students/{sid}/status")
async def change_status(sid: str, payload: StatusChange, request: Request, user: dict = Depends(require_permission(P_STUDENT_STATUS_MANAGE))):
    if payload.status not in LIFECYCLE_STATES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {LIFECYCLE_STATES}")
    db = get_db()
    old = await db.students.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Student not found")
    updates = {
        "status": payload.status, "status_reason": payload.reason,
        "status_effective_date": payload.effective_date or datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.students.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.students.find_one({"_id": old["_id"]})
    await log_event(action="student.status.change", resource="student", resource_id=sid,
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={"status": old.get("status")}, new_value={"status": payload.status},
                    metadata={"reason": payload.reason})
    return _out(new)


# ============================================================
# Enrollments
# ============================================================
@router.get("/students/{sid}/enrollments")
async def list_enrollments(sid: str, user: dict = Depends(require_permission(P_STUDENT_ENROLL_VIEW))):
    db = get_db()
    if not await db.students.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Student not found")
    docs = await db.student_enrollments.find({"tenant_id": user["tenant_id"], "student_id": sid}).sort("start_date", -1).to_list(200)
    return [_out(d) for d in docs]


@router.post("/students/{sid}/enrollments", status_code=201)
async def create_enrollment(sid: str, payload: CreateEnrollment, request: Request, user: dict = Depends(require_permission(P_STUDENT_ENROLL_MANAGE))):
    db = get_db()
    if not await db.students.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Student not found")
    dup = await db.student_enrollments.find_one({
        "tenant_id": user["tenant_id"], "student_id": sid,
        "academic_year": payload.academic_year, "enrollment_status": "active",
    })
    if dup:
        raise HTTPException(status_code=409, detail="Student already has active enrollment for this academic year")
    doc = StudentEnrollment(
        tenant_id=user["tenant_id"], student_id=sid,
        academic_year=payload.academic_year, class_name=payload.class_name,
        section=payload.section, roll_number=payload.roll_number, house=payload.house,
        start_date=payload.start_date or datetime.now(timezone.utc).isoformat(),
        remarks=payload.remarks, enrollment_status="active",
    ).to_mongo()
    res = await db.student_enrollments.insert_one(doc); doc["_id"] = res.inserted_id
    # Update the snapshot on the Student.
    await db.students.update_one({"_id": _oid(sid)}, {"$set": {
        "academic_year": payload.academic_year, "class_name": payload.class_name,
        "section": payload.section, "roll_number": payload.roll_number, "house": payload.house,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }})
    await log_event(action="student.enrollment.create", resource="student_enrollment",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"], actor=user, request=request,
                    metadata={"student_id": sid, "academic_year": payload.academic_year})
    return _out(doc)


@router.patch("/enrollments/{eid}")
async def update_enrollment(eid: str, payload: UpdateEnrollment, request: Request, user: dict = Depends(require_permission(P_STUDENT_ENROLL_MANAGE))):
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    db = get_db()
    old = await db.student_enrollments.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Enrollment not found")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.student_enrollments.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.student_enrollments.find_one({"_id": old["_id"]})
    await log_event(action="student.enrollment.update", resource="student_enrollment", resource_id=eid,
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(new)


# ============================================================
# Guardians
# ============================================================
@router.get("/guardians")
async def list_guardians(q: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200), user: dict = Depends(require_permission(P_GUARDIAN_VIEW))):
    query: dict = {"tenant_id": user["tenant_id"]}
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [{"first_name": rx}, {"last_name": rx}, {"mobile_primary": rx}, {"email": rx}]
    db = get_db()
    total = await db.guardians.count_documents(query)
    docs = await db.guardians.find(query).sort("created_at", -1).skip((page-1)*page_size).limit(page_size).to_list(page_size)
    return {"items": [_out(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.post("/guardians", status_code=201)
async def create_guardian(payload: CreateGuardian, request: Request, user: dict = Depends(require_permission(P_GUARDIAN_CREATE))):
    doc = Guardian(
        tenant_id=user["tenant_id"], first_name=payload.first_name, middle_name=payload.middle_name,
        last_name=payload.last_name, relationship_type=payload.relationship_type,
        mobile_primary=payload.mobile_primary, mobile_secondary=payload.mobile_secondary,
        email=(payload.email.lower() if payload.email else None),
        occupation=payload.occupation, employer=payload.employer, address=payload.address,
        emergency_contact_flag=payload.emergency_contact_flag, family_id=payload.family_id,
    ).to_mongo()
    res = await get_db().guardians.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="guardian.create", resource="guardian", resource_id=str(res.inserted_id),
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    new_value={"mobile_primary": payload.mobile_primary})
    return _out(doc)


@router.get("/guardians/{gid}")
async def get_guardian(gid: str, user: dict = Depends(require_permission(P_GUARDIAN_VIEW))):
    d = await get_db().guardians.find_one({"_id": _oid(gid), "tenant_id": user["tenant_id"]})
    if not d: raise HTTPException(status_code=404, detail="Guardian not found")
    return _out(d)


@router.get("/guardians/{gid}/students")
async def guardian_students(gid: str, user: dict = Depends(require_permission(P_STUDENT_GUARDIAN_VIEW))):
    db = get_db()
    if not await db.guardians.find_one({"_id": _oid(gid), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Guardian not found")
    rels = await db.student_guardians.find({"tenant_id": user["tenant_id"], "guardian_id": gid, "end_date": None}).to_list(100)
    result = []
    for r in rels:
        r = _out(r)
        s = await db.students.find_one({"_id": _oid(r["student_id"]), "tenant_id": user["tenant_id"]})
        if s: r["student"] = _out(s)
        result.append(r)
    return result


@router.patch("/guardians/{gid}")
async def update_guardian(gid: str, payload: UpdateGuardian, request: Request, user: dict = Depends(require_permission(P_GUARDIAN_UPDATE))):
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    if updates.get("email"): updates["email"] = updates["email"].lower()
    db = get_db()
    old = await db.guardians.find_one({"_id": _oid(gid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Guardian not found")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.guardians.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.guardians.find_one({"_id": old["_id"]})
    await log_event(action="guardian.update", resource="guardian", resource_id=gid,
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(new)


# ============================================================
# Student-Guardian relationships
# ============================================================
@router.get("/students/{sid}/guardians")
async def student_guardians(sid: str, user: dict = Depends(require_permission(P_STUDENT_GUARDIAN_VIEW))):
    db = get_db()
    if not await db.students.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Student not found")
    rels = await db.student_guardians.find({"tenant_id": user["tenant_id"], "student_id": sid, "end_date": None}).to_list(50)
    result = []
    for r in rels:
        r = _out(r)
        g = await db.guardians.find_one({"_id": _oid(r["guardian_id"]), "tenant_id": user["tenant_id"]})
        if g: r["guardian"] = _out(g)
        result.append(r)
    return result


@router.post("/students/{sid}/guardians", status_code=201)
async def link_guardian(sid: str, payload: LinkGuardian, request: Request, user: dict = Depends(require_permission(P_STUDENT_GUARDIAN_MANAGE))):
    db = get_db()
    if not await db.students.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Student not found")
    if not await db.guardians.find_one({"_id": _oid(payload.guardian_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Guardian not found")
    existing = await db.student_guardians.find_one({
        "tenant_id": user["tenant_id"], "student_id": sid, "guardian_id": payload.guardian_id, "end_date": None,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Guardian is already linked to this student")
    doc = StudentGuardian(
        tenant_id=user["tenant_id"], student_id=sid, guardian_id=payload.guardian_id,
        relationship_type=payload.relationship_type, is_primary=payload.is_primary,
        is_emergency_contact=payload.is_emergency_contact,
        has_pickup_authorization=payload.has_pickup_authorization,
        has_fee_responsibility=payload.has_fee_responsibility,
        has_academic_access=payload.has_academic_access,
        communication_priority=payload.communication_priority,
        start_date=datetime.now(timezone.utc).isoformat(),
    ).to_mongo()
    res = await db.student_guardians.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="student.guardian.link", resource="student_guardian", resource_id=str(res.inserted_id),
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    metadata={"student_id": sid, "guardian_id": payload.guardian_id})
    return _out(doc)


@router.patch("/student-guardians/{rid}")
async def update_rel(rid: str, payload: UpdateRelationship, request: Request, user: dict = Depends(require_permission(P_STUDENT_GUARDIAN_MANAGE))):
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    db = get_db()
    old = await db.student_guardians.find_one({"_id": _oid(rid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Relationship not found")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.student_guardians.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.student_guardians.find_one({"_id": old["_id"]})
    await log_event(action="student.guardian.update", resource="student_guardian", resource_id=rid,
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(new)


@router.delete("/student-guardians/{rid}")
async def unlink_guardian(rid: str, request: Request, user: dict = Depends(require_permission(P_STUDENT_GUARDIAN_MANAGE))):
    db = get_db()
    old = await db.student_guardians.find_one({"_id": _oid(rid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Relationship not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.student_guardians.update_one({"_id": old["_id"]}, {"$set": {"end_date": now, "updated_at": now}})
    await log_event(action="student.guardian.unlink", resource="student_guardian", resource_id=rid,
                    tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Families
# ============================================================
@router.get("/families")
async def list_families(user: dict = Depends(require_permission(P_FAMILY_VIEW))):
    docs = await get_db().families.find({"tenant_id": user["tenant_id"]}).sort("created_at", -1).to_list(500)
    return [_out(d) for d in docs]


@router.post("/families", status_code=201)
async def create_family(payload: CreateFamily, request: Request, user: dict = Depends(require_permission(P_FAMILY_MANAGE))):
    doc = Family(tenant_id=user["tenant_id"], family_name=payload.family_name,
                 primary_contact_guardian_id=payload.primary_contact_guardian_id,
                 address=payload.address, notes=payload.notes).to_mongo()
    res = await get_db().families.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="family.create", resource="family", resource_id=str(res.inserted_id),
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    new_value={"family_name": payload.family_name})
    return _out(doc)


@router.get("/families/{fid}")
async def get_family(fid: str, user: dict = Depends(require_permission(P_FAMILY_VIEW))):
    db = get_db()
    f = await db.families.find_one({"_id": _oid(fid), "tenant_id": user["tenant_id"]})
    if not f: raise HTTPException(status_code=404, detail="Family not found")
    students = [_out(s) for s in await db.students.find({"tenant_id": user["tenant_id"], "family_id": fid}).to_list(200)]
    guardians = [_out(g) for g in await db.guardians.find({"tenant_id": user["tenant_id"], "family_id": fid}).to_list(200)]
    return {**_out(f), "students": students, "guardians": guardians}


@router.patch("/families/{fid}")
async def update_family(fid: str, payload: UpdateFamily, request: Request, user: dict = Depends(require_permission(P_FAMILY_MANAGE))):
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    db = get_db()
    old = await db.families.find_one({"_id": _oid(fid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Family not found")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.families.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.families.find_one({"_id": old["_id"]})
    await log_event(action="family.update", resource="family", resource_id=fid,
                    tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(new)
