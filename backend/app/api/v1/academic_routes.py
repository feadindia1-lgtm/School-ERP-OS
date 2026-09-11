"""Academic Structure & School Calendar routes — Prompt 4.

Single canonical academic framework used by Attendance, Fees, Timetable,
Exams and Curriculum.  All routes are tenant-scoped, RBAC-gated and
audit-logged.

Endpoints
---------
- /school/academic/years                     [GET/POST]
- /school/academic/years/{id}                [GET/PATCH]
- /school/academic/years/{id}/set-current    [POST]
- /school/academic/years/{id}/archive        [POST]
- /school/academic/board-config              [GET/PATCH]
- /school/academic/classes                   [GET/POST]
- /school/academic/classes/{id}              [GET/PATCH/DELETE]
- /school/academic/sections                  [GET/POST]
- /school/academic/sections/{id}             [GET/PATCH/DELETE]
- /school/academic/subjects                  [GET/POST]
- /school/academic/subjects/{id}             [GET/PATCH/DELETE]
- /school/academic/subject-groups            [GET/POST]
- /school/academic/subject-groups/{id}       [GET/PATCH/DELETE]
- /school/academic/rooms                     [GET/POST]
- /school/academic/rooms/{id}                [GET/PATCH/DELETE]
- /school/academic/bell-schedules            [GET/POST]
- /school/academic/bell-schedules/{id}       [GET/PATCH/DELETE]
- /school/academic/working-day-policy        [GET/PUT]  (one per year)
- /school/academic/holidays                  [GET/POST]
- /school/academic/holidays/{id}             [PATCH/DELETE]
- /school/academic/teacher-assignments       [GET/POST]
- /school/academic/teacher-assignments/{id}  [PATCH/DELETE]
- /school/academic/overview/{year_id}        [GET]  — dashboard
"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.core.deps import require_permission
from app.core.permissions import (
    P_ACADEMIC_ASSIGN_MANAGE, P_ACADEMIC_BOARD_CONFIG,
    P_ACADEMIC_CALENDAR_MANAGE, P_ACADEMIC_CLASS_MANAGE,
    P_ACADEMIC_ROOM_MANAGE, P_ACADEMIC_SCHEDULE_MANAGE,
    P_ACADEMIC_SECTION_MANAGE, P_ACADEMIC_SUBJECT_MANAGE, P_ACADEMIC_VIEW,
    P_ACADEMIC_YEAR_MANAGE,
)
from app.models.academic import (
    ACADEMIC_YEAR_STATUSES, BOARD_PRESETS, ROOM_TYPES, SUBJECT_TYPES, WEEKDAYS,
    AcademicClass, AcademicSection, AcademicYear, BellSchedule, BoardConfig,
    Holiday, Room, Subject, SubjectGroup, TeacherAssignment, WorkingDayPolicy,
)
from app.services.audit_service import log_event

router = APIRouter(prefix="/school/academic", tags=["academic"])


def _oid(v: str) -> ObjectId:
    try: return ObjectId(v)
    except InvalidId: raise HTTPException(status_code=404, detail="Not found")


def _out(d: dict) -> dict:
    d = dict(d); d["id"] = str(d.pop("_id")); return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get_year(db, tid: str, year_id: str) -> dict:
    d = await db.academic_years.find_one({"_id": _oid(year_id), "tenant_id": tid})
    if not d: raise HTTPException(status_code=404, detail="Academic year not found")
    return d


async def _assert_year_editable(db, tid: str, year_id: str) -> dict:
    """Historical (archived) years are read-only."""
    y = await _get_year(db, tid, year_id)
    if y.get("status") == "archived":
        raise HTTPException(
            status_code=409,
            detail={"code": "year_archived", "message": "Academic year is archived and read-only"},
        )
    return y


# ============================================================
# Board config
# ============================================================
@router.get("/board-config")
async def get_board_config(user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    db = get_db()
    cfg = await db.board_configs.find_one({"tenant_id": user["tenant_id"]})
    if cfg:
        return {**_out(cfg), "presets": BOARD_PRESETS}
    # Seed from tenant.board on first read
    tenant = await db.tenants.find_one({"_id": _oid(user["tenant_id"])})
    board = (tenant or {}).get("board") or "CBSE"
    if board not in BOARD_PRESETS:
        board = "CBSE"
    preset = BOARD_PRESETS[board]
    doc = BoardConfig(
        tenant_id=user["tenant_id"], board=board,
        class_label=preset["class_label"], section_label=preset["section_label"],
        terms=list(preset["terms"]),
    ).to_mongo()
    res = await db.board_configs.insert_one(doc); doc["_id"] = res.inserted_id
    return {**_out(doc), "presets": BOARD_PRESETS}


class UpdateBoardConfig(BaseModel):
    board: str | None = None
    class_label: str | None = None
    section_label: str | None = None
    terms: list[str] | None = None
    marking_style: str | None = None


@router.patch("/board-config")
async def update_board_config(payload: UpdateBoardConfig, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_BOARD_CONFIG))):
    db = get_db()
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    if "board" in updates and updates["board"] not in BOARD_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown board. Allowed: {list(BOARD_PRESETS)}")
    updates["updated_at"] = _now_iso()
    old = await db.board_configs.find_one({"tenant_id": user["tenant_id"]})
    if old:
        await db.board_configs.update_one({"_id": old["_id"]}, {"$set": updates})
    else:
        base = BoardConfig(tenant_id=user["tenant_id"], **{k: v for k, v in updates.items() if k != "updated_at"}).to_mongo()
        await db.board_configs.insert_one(base)
    await log_event(action="academic.board.update", resource="board_config",
                    resource_id=user["tenant_id"], tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value=updates)
    cfg = await db.board_configs.find_one({"tenant_id": user["tenant_id"]})
    return {**_out(cfg), "presets": BOARD_PRESETS}


# ============================================================
# Academic years
# ============================================================
class CreateYear(BaseModel):
    name: str = Field(min_length=2, max_length=32)
    start_date: str
    end_date: str
    is_current: bool = False
    board_preset: str = "CBSE"
    term_names: list[str] = Field(default_factory=list)
    notes: str | None = None


class UpdateYear(BaseModel):
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    board_preset: str | None = None
    term_names: list[str] | None = None
    notes: str | None = None


@router.get("/years")
async def list_years(user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    docs = await get_db().academic_years.find({"tenant_id": user["tenant_id"]}).sort("start_date", -1).to_list(200)
    return [_out(d) for d in docs]


@router.post("/years", status_code=201)
async def create_year(payload: CreateYear, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_YEAR_MANAGE))):
    db = get_db()
    if payload.start_date >= payload.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    if payload.board_preset not in BOARD_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown board preset. Allowed: {list(BOARD_PRESETS)}")
    if await db.academic_years.find_one({"tenant_id": user["tenant_id"], "name": payload.name}):
        raise HTTPException(status_code=409, detail={"code": "duplicate_year", "message": "Academic year name already exists"})
    if payload.is_current:
        await db.academic_years.update_many({"tenant_id": user["tenant_id"]}, {"$set": {"is_current": False}})
    term_names = payload.term_names or list(BOARD_PRESETS[payload.board_preset]["terms"])
    doc = AcademicYear(
        tenant_id=user["tenant_id"], name=payload.name,
        start_date=payload.start_date, end_date=payload.end_date,
        is_current=payload.is_current,
        status="current" if payload.is_current else "planning",
        board_preset=payload.board_preset,
        term_names=term_names, notes=payload.notes,
    ).to_mongo()
    res = await db.academic_years.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="academic.year.create", resource="academic_year",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"name": payload.name})
    return _out(doc)


@router.get("/years/{yid}")
async def get_year_endpoint(yid: str, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    return _out(await _get_year(get_db(), user["tenant_id"], yid))


@router.patch("/years/{yid}")
async def update_year(yid: str, payload: UpdateYear, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_YEAR_MANAGE))):
    db = get_db()
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    old = await _assert_year_editable(db, user["tenant_id"], yid)
    if updates.get("start_date") and updates.get("end_date") and updates["start_date"] >= updates["end_date"]:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    if updates.get("board_preset") and updates["board_preset"] not in BOARD_PRESETS:
        raise HTTPException(status_code=400, detail="Unknown board preset")
    updates["updated_at"] = _now_iso()
    await db.academic_years.update_one({"_id": old["_id"]}, {"$set": updates})
    new = await db.academic_years.find_one({"_id": old["_id"]})
    await log_event(action="academic.year.update", resource="academic_year",
                    resource_id=yid, tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(new)


@router.post("/years/{yid}/set-current")
async def set_current_year(yid: str, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_YEAR_MANAGE))):
    db = get_db()
    y = await _get_year(db, user["tenant_id"], yid)
    if y.get("status") == "archived":
        raise HTTPException(status_code=409, detail={"code": "year_archived", "message": "Cannot activate archived year"})
    await db.academic_years.update_many({"tenant_id": user["tenant_id"], "is_current": True}, {"$set": {"is_current": False, "status": "planning"}})
    await db.academic_years.update_one({"_id": y["_id"]}, {"$set": {"is_current": True, "status": "current", "updated_at": _now_iso()}})
    await log_event(action="academic.year.set_current", resource="academic_year",
                    resource_id=yid, tenant_id=user["tenant_id"], actor=user, request=request)
    return _out(await db.academic_years.find_one({"_id": y["_id"]}))


@router.post("/years/{yid}/archive")
async def archive_year(yid: str, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_YEAR_MANAGE))):
    db = get_db()
    y = await _get_year(db, user["tenant_id"], yid)
    if y.get("is_current"):
        raise HTTPException(status_code=409, detail={"code": "year_current", "message": "Cannot archive the current year — set another year as current first"})
    await db.academic_years.update_one({"_id": y["_id"]}, {"$set": {"status": "archived", "updated_at": _now_iso()}})
    await log_event(action="academic.year.archive", resource="academic_year",
                    resource_id=yid, tenant_id=user["tenant_id"], actor=user, request=request)
    return _out(await db.academic_years.find_one({"_id": y["_id"]}))


# ============================================================
# Classes
# ============================================================
class CreateClass(BaseModel):
    academic_year_id: str
    name: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=40)
    stream: str | None = None
    order: int = 0
    description: str | None = None


class UpdateClass(BaseModel):
    name: str | None = None
    code: str | None = None
    stream: str | None = None
    order: int | None = None
    description: str | None = None


@router.get("/classes")
async def list_classes(academic_year_id: str | None = None, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    q: dict = {"tenant_id": user["tenant_id"]}
    if academic_year_id: q["academic_year_id"] = academic_year_id
    docs = await get_db().academic_classes.find(q).sort("order", 1).to_list(500)
    return [_out(d) for d in docs]


@router.post("/classes", status_code=201)
async def create_class(payload: CreateClass, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_CLASS_MANAGE))):
    db = get_db()
    await _assert_year_editable(db, user["tenant_id"], payload.academic_year_id)
    if await db.academic_classes.find_one({"tenant_id": user["tenant_id"], "academic_year_id": payload.academic_year_id, "code": payload.code}):
        raise HTTPException(status_code=409, detail={"code": "duplicate_class", "message": "Class code already exists for this year"})
    doc = AcademicClass(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.academic_classes.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="academic.class.create", resource="academic_class",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"code": payload.code})
    return _out(doc)


@router.get("/classes/{cid}")
async def get_class(cid: str, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    d = await get_db().academic_classes.find_one({"_id": _oid(cid), "tenant_id": user["tenant_id"]})
    if not d: raise HTTPException(status_code=404, detail="Class not found")
    return _out(d)


@router.patch("/classes/{cid}")
async def update_class(cid: str, payload: UpdateClass, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_CLASS_MANAGE))):
    db = get_db()
    old = await db.academic_classes.find_one({"_id": _oid(cid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Class not found")
    await _assert_year_editable(db, user["tenant_id"], old["academic_year_id"])
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    if "code" in updates and updates["code"] != old["code"]:
        if await db.academic_classes.find_one({"tenant_id": user["tenant_id"], "academic_year_id": old["academic_year_id"], "code": updates["code"]}):
            raise HTTPException(status_code=409, detail="Class code already exists")
    updates["updated_at"] = _now_iso()
    await db.academic_classes.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="academic.class.update", resource="academic_class",
                    resource_id=cid, tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(await db.academic_classes.find_one({"_id": old["_id"]}))


@router.delete("/classes/{cid}")
async def delete_class(cid: str, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_CLASS_MANAGE))):
    db = get_db()
    old = await db.academic_classes.find_one({"_id": _oid(cid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Class not found")
    await _assert_year_editable(db, user["tenant_id"], old["academic_year_id"])
    if await db.academic_sections.count_documents({"tenant_id": user["tenant_id"], "class_id": cid}) > 0:
        raise HTTPException(status_code=409, detail={"code": "class_in_use", "message": "Class has sections. Delete sections first."})
    await db.academic_classes.delete_one({"_id": old["_id"]})
    await log_event(action="academic.class.delete", resource="academic_class",
                    resource_id=cid, tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={"code": old.get("code")})
    return {"ok": True}


# ============================================================
# Sections
# ============================================================
class CreateSection(BaseModel):
    academic_year_id: str
    class_id: str
    name: str = Field(min_length=1, max_length=40)
    capacity: int | None = None
    class_teacher_user_id: str | None = None
    room_id: str | None = None
    notes: str | None = None


class UpdateSection(BaseModel):
    name: str | None = None
    capacity: int | None = None
    class_teacher_user_id: str | None = None
    room_id: str | None = None
    notes: str | None = None


@router.get("/sections")
async def list_sections(academic_year_id: str | None = None, class_id: str | None = None, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    q: dict = {"tenant_id": user["tenant_id"]}
    if academic_year_id: q["academic_year_id"] = academic_year_id
    if class_id: q["class_id"] = class_id
    docs = await get_db().academic_sections.find(q).sort("name", 1).to_list(1000)
    return [_out(d) for d in docs]


@router.post("/sections", status_code=201)
async def create_section(payload: CreateSection, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SECTION_MANAGE))):
    db = get_db()
    await _assert_year_editable(db, user["tenant_id"], payload.academic_year_id)
    parent = await db.academic_classes.find_one({"_id": _oid(payload.class_id), "tenant_id": user["tenant_id"]})
    if not parent: raise HTTPException(status_code=404, detail="Class not found")
    if parent["academic_year_id"] != payload.academic_year_id:
        raise HTTPException(status_code=400, detail="class_id belongs to a different academic year")
    if await db.academic_sections.find_one({"tenant_id": user["tenant_id"], "class_id": payload.class_id, "name": payload.name}):
        raise HTTPException(status_code=409, detail={"code": "duplicate_section", "message": "Section name already exists in this class"})
    if payload.class_teacher_user_id:
        u = await db.users.find_one({"_id": _oid(payload.class_teacher_user_id), "tenant_id": user["tenant_id"]})
        if not u or u.get("role") not in {"teacher", "class_teacher"}:
            raise HTTPException(status_code=400, detail="class_teacher_user_id must reference a user with role teacher/class_teacher")
    doc = AcademicSection(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.academic_sections.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="academic.section.create", resource="academic_section",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"name": payload.name, "class_id": payload.class_id})
    return _out(doc)


@router.get("/sections/{sid}")
async def get_section(sid: str, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    d = await get_db().academic_sections.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]})
    if not d: raise HTTPException(status_code=404, detail="Section not found")
    return _out(d)


@router.patch("/sections/{sid}")
async def update_section(sid: str, payload: UpdateSection, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SECTION_MANAGE))):
    db = get_db()
    old = await db.academic_sections.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Section not found")
    await _assert_year_editable(db, user["tenant_id"], old["academic_year_id"])
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    if "name" in updates and updates["name"] != old["name"]:
        if await db.academic_sections.find_one({"tenant_id": user["tenant_id"], "class_id": old["class_id"], "name": updates["name"]}):
            raise HTTPException(status_code=409, detail="Section name already exists")
    if updates.get("class_teacher_user_id"):
        u = await db.users.find_one({"_id": _oid(updates["class_teacher_user_id"]), "tenant_id": user["tenant_id"]})
        if not u or u.get("role") not in {"teacher", "class_teacher"}:
            raise HTTPException(status_code=400, detail="class_teacher_user_id must reference a teacher")
    updates["updated_at"] = _now_iso()
    await db.academic_sections.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="academic.section.update", resource="academic_section",
                    resource_id=sid, tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(await db.academic_sections.find_one({"_id": old["_id"]}))


@router.delete("/sections/{sid}")
async def delete_section(sid: str, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SECTION_MANAGE))):
    db = get_db()
    old = await db.academic_sections.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Section not found")
    await _assert_year_editable(db, user["tenant_id"], old["academic_year_id"])
    await db.academic_sections.delete_one({"_id": old["_id"]})
    await log_event(action="academic.section.delete", resource="academic_section",
                    resource_id=sid, tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Subjects
# ============================================================
class CreateSubject(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    subject_type: str = "theory"
    is_optional: bool = False
    description: str | None = None


class UpdateSubject(BaseModel):
    name: str | None = None
    code: str | None = None
    subject_type: str | None = None
    is_optional: bool | None = None
    description: str | None = None


@router.get("/subjects")
async def list_subjects(user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    docs = await get_db().subjects.find({"tenant_id": user["tenant_id"]}).sort("name", 1).to_list(1000)
    return [_out(d) for d in docs]


@router.post("/subjects", status_code=201)
async def create_subject(payload: CreateSubject, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SUBJECT_MANAGE))):
    db = get_db()
    if payload.subject_type not in SUBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown subject_type. Allowed: {SUBJECT_TYPES}")
    if await db.subjects.find_one({"tenant_id": user["tenant_id"], "code": payload.code}):
        raise HTTPException(status_code=409, detail={"code": "duplicate_subject", "message": "Subject code already exists"})
    doc = Subject(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.subjects.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="academic.subject.create", resource="subject",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"code": payload.code})
    return _out(doc)


@router.get("/subjects/{sid}")
async def get_subject(sid: str, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    d = await get_db().subjects.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]})
    if not d: raise HTTPException(status_code=404, detail="Subject not found")
    return _out(d)


@router.patch("/subjects/{sid}")
async def update_subject(sid: str, payload: UpdateSubject, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SUBJECT_MANAGE))):
    db = get_db()
    old = await db.subjects.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Subject not found")
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    if updates.get("subject_type") and updates["subject_type"] not in SUBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown subject_type. Allowed: {SUBJECT_TYPES}")
    if "code" in updates and updates["code"] != old["code"]:
        if await db.subjects.find_one({"tenant_id": user["tenant_id"], "code": updates["code"]}):
            raise HTTPException(status_code=409, detail="Subject code already exists")
    updates["updated_at"] = _now_iso()
    await db.subjects.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="academic.subject.update", resource="subject",
                    resource_id=sid, tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(await db.subjects.find_one({"_id": old["_id"]}))


@router.delete("/subjects/{sid}")
async def delete_subject(sid: str, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SUBJECT_MANAGE))):
    db = get_db()
    old = await db.subjects.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Subject not found")
    in_use = await db.teacher_assignments.count_documents({"tenant_id": user["tenant_id"], "subject_id": sid})
    in_groups = await db.subject_groups.count_documents({"tenant_id": user["tenant_id"], "subject_ids": sid})
    if in_use or in_groups:
        raise HTTPException(status_code=409, detail={"code": "subject_in_use", "message": "Subject is referenced by assignments or groups"})
    await db.subjects.delete_one({"_id": old["_id"]})
    await log_event(action="academic.subject.delete", resource="subject",
                    resource_id=sid, tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Subject groups
# ============================================================
class CreateSubjectGroup(BaseModel):
    academic_year_id: str
    class_id: str
    name: str = Field(min_length=1, max_length=120)
    subject_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class UpdateSubjectGroup(BaseModel):
    name: str | None = None
    subject_ids: list[str] | None = None
    notes: str | None = None


@router.get("/subject-groups")
async def list_subject_groups(academic_year_id: str | None = None, class_id: str | None = None, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    q: dict = {"tenant_id": user["tenant_id"]}
    if academic_year_id: q["academic_year_id"] = academic_year_id
    if class_id: q["class_id"] = class_id
    docs = await get_db().subject_groups.find(q).sort("name", 1).to_list(500)
    return [_out(d) for d in docs]


@router.post("/subject-groups", status_code=201)
async def create_subject_group(payload: CreateSubjectGroup, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SUBJECT_MANAGE))):
    db = get_db()
    await _assert_year_editable(db, user["tenant_id"], payload.academic_year_id)
    if not await db.academic_classes.find_one({"_id": _oid(payload.class_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Class not found")
    for sid in payload.subject_ids:
        if not await db.subjects.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]}):
            raise HTTPException(status_code=400, detail=f"Subject {sid} not found")
    doc = SubjectGroup(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.subject_groups.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="academic.subject_group.create", resource="subject_group",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"name": payload.name})
    return _out(doc)


@router.get("/subject-groups/{gid}")
async def get_subject_group(gid: str, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    d = await get_db().subject_groups.find_one({"_id": _oid(gid), "tenant_id": user["tenant_id"]})
    if not d: raise HTTPException(status_code=404, detail="Subject group not found")
    return _out(d)


@router.patch("/subject-groups/{gid}")
async def update_subject_group(gid: str, payload: UpdateSubjectGroup, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SUBJECT_MANAGE))):
    db = get_db()
    old = await db.subject_groups.find_one({"_id": _oid(gid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Subject group not found")
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    if "subject_ids" in updates:
        for sid in updates["subject_ids"]:
            if not await db.subjects.find_one({"_id": _oid(sid), "tenant_id": user["tenant_id"]}):
                raise HTTPException(status_code=400, detail=f"Subject {sid} not found")
    updates["updated_at"] = _now_iso()
    await db.subject_groups.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="academic.subject_group.update", resource="subject_group",
                    resource_id=gid, tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(await db.subject_groups.find_one({"_id": old["_id"]}))


@router.delete("/subject-groups/{gid}")
async def delete_subject_group(gid: str, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SUBJECT_MANAGE))):
    db = get_db()
    old = await db.subject_groups.find_one({"_id": _oid(gid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Subject group not found")
    await db.subject_groups.delete_one({"_id": old["_id"]})
    await log_event(action="academic.subject_group.delete", resource="subject_group",
                    resource_id=gid, tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Rooms
# ============================================================
class CreateRoom(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    room_type: str = "classroom"
    capacity: int | None = None
    floor: str | None = None
    building: str | None = None
    description: str | None = None


class UpdateRoom(BaseModel):
    name: str | None = None
    code: str | None = None
    room_type: str | None = None
    capacity: int | None = None
    floor: str | None = None
    building: str | None = None
    description: str | None = None


@router.get("/rooms")
async def list_rooms(user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    docs = await get_db().rooms.find({"tenant_id": user["tenant_id"]}).sort("code", 1).to_list(500)
    return [_out(d) for d in docs]


@router.post("/rooms", status_code=201)
async def create_room(payload: CreateRoom, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_ROOM_MANAGE))):
    db = get_db()
    if payload.room_type not in ROOM_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown room_type. Allowed: {ROOM_TYPES}")
    if await db.rooms.find_one({"tenant_id": user["tenant_id"], "code": payload.code}):
        raise HTTPException(status_code=409, detail={"code": "duplicate_room", "message": "Room code already exists"})
    doc = Room(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.rooms.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="academic.room.create", resource="room",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"code": payload.code})
    return _out(doc)


@router.get("/rooms/{rid}")
async def get_room(rid: str, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    d = await get_db().rooms.find_one({"_id": _oid(rid), "tenant_id": user["tenant_id"]})
    if not d: raise HTTPException(status_code=404, detail="Room not found")
    return _out(d)


@router.patch("/rooms/{rid}")
async def update_room(rid: str, payload: UpdateRoom, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_ROOM_MANAGE))):
    db = get_db()
    old = await db.rooms.find_one({"_id": _oid(rid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Room not found")
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    if updates.get("room_type") and updates["room_type"] not in ROOM_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown room_type. Allowed: {ROOM_TYPES}")
    if "code" in updates and updates["code"] != old["code"]:
        if await db.rooms.find_one({"tenant_id": user["tenant_id"], "code": updates["code"]}):
            raise HTTPException(status_code=409, detail="Room code already exists")
    updates["updated_at"] = _now_iso()
    await db.rooms.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="academic.room.update", resource="room",
                    resource_id=rid, tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(await db.rooms.find_one({"_id": old["_id"]}))


@router.delete("/rooms/{rid}")
async def delete_room(rid: str, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_ROOM_MANAGE))):
    db = get_db()
    old = await db.rooms.find_one({"_id": _oid(rid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Room not found")
    if await db.academic_sections.count_documents({"tenant_id": user["tenant_id"], "room_id": rid}):
        raise HTTPException(status_code=409, detail={"code": "room_in_use", "message": "Room is assigned to sections"})
    await db.rooms.delete_one({"_id": old["_id"]})
    await log_event(action="academic.room.delete", resource="room",
                    resource_id=rid, tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Bell schedules
# ============================================================
def _validate_periods(periods: list[dict]) -> None:
    """Ensure period ordering and no time overlaps."""
    if not periods: return
    seen_numbers: set[int] = set()
    prev_end: str | None = None
    for i, p in enumerate(periods):
        pno = p.get("period_no")
        if not isinstance(pno, int):
            raise HTTPException(status_code=400, detail=f"periods[{i}].period_no must be int")
        if pno in seen_numbers:
            raise HTTPException(status_code=409, detail={"code": "duplicate_period_no", "message": f"Period {pno} declared twice"})
        seen_numbers.add(pno)
        st, en = p.get("start_time"), p.get("end_time")
        if not st or not en:
            raise HTTPException(status_code=400, detail=f"periods[{i}] missing start_time/end_time")
        if st >= en:
            raise HTTPException(status_code=400, detail=f"periods[{i}] start_time must be before end_time")
        if prev_end and st < prev_end:
            raise HTTPException(status_code=409, detail={"code": "period_overlap", "message": f"Period {pno} overlaps previous"})
        prev_end = en


class CreateBellSchedule(BaseModel):
    academic_year_id: str
    name: str = Field(min_length=1, max_length=120)
    is_default: bool = False
    periods: list[dict] = Field(default_factory=list)
    notes: str | None = None


class UpdateBellSchedule(BaseModel):
    name: str | None = None
    is_default: bool | None = None
    periods: list[dict] | None = None
    notes: str | None = None


@router.get("/bell-schedules")
async def list_bell_schedules(academic_year_id: str | None = None, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    q: dict = {"tenant_id": user["tenant_id"]}
    if academic_year_id: q["academic_year_id"] = academic_year_id
    docs = await get_db().bell_schedules.find(q).sort("name", 1).to_list(50)
    return [_out(d) for d in docs]


@router.post("/bell-schedules", status_code=201)
async def create_bell_schedule(payload: CreateBellSchedule, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SCHEDULE_MANAGE))):
    db = get_db()
    await _assert_year_editable(db, user["tenant_id"], payload.academic_year_id)
    _validate_periods(payload.periods)
    if await db.bell_schedules.find_one({"tenant_id": user["tenant_id"], "academic_year_id": payload.academic_year_id, "name": payload.name}):
        raise HTTPException(status_code=409, detail={"code": "duplicate_bell_schedule", "message": "Bell schedule name already exists for this year"})
    if payload.is_default:
        await db.bell_schedules.update_many({"tenant_id": user["tenant_id"], "academic_year_id": payload.academic_year_id}, {"$set": {"is_default": False}})
    doc = BellSchedule(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.bell_schedules.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="academic.bell.create", resource="bell_schedule",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"name": payload.name})
    return _out(doc)


@router.get("/bell-schedules/{bid}")
async def get_bell_schedule(bid: str, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    d = await get_db().bell_schedules.find_one({"_id": _oid(bid), "tenant_id": user["tenant_id"]})
    if not d: raise HTTPException(status_code=404, detail="Bell schedule not found")
    return _out(d)


@router.patch("/bell-schedules/{bid}")
async def update_bell_schedule(bid: str, payload: UpdateBellSchedule, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SCHEDULE_MANAGE))):
    db = get_db()
    old = await db.bell_schedules.find_one({"_id": _oid(bid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Bell schedule not found")
    await _assert_year_editable(db, user["tenant_id"], old["academic_year_id"])
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    if "periods" in updates: _validate_periods(updates["periods"])
    if updates.get("is_default"):
        await db.bell_schedules.update_many({"tenant_id": user["tenant_id"], "academic_year_id": old["academic_year_id"]}, {"$set": {"is_default": False}})
    updates["updated_at"] = _now_iso()
    await db.bell_schedules.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="academic.bell.update", resource="bell_schedule",
                    resource_id=bid, tenant_id=user["tenant_id"], actor=user, request=request,
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(await db.bell_schedules.find_one({"_id": old["_id"]}))


@router.delete("/bell-schedules/{bid}")
async def delete_bell_schedule(bid: str, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_SCHEDULE_MANAGE))):
    db = get_db()
    old = await db.bell_schedules.find_one({"_id": _oid(bid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Bell schedule not found")
    await _assert_year_editable(db, user["tenant_id"], old["academic_year_id"])
    await db.bell_schedules.delete_one({"_id": old["_id"]})
    await log_event(action="academic.bell.delete", resource="bell_schedule",
                    resource_id=bid, tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Working-day policy — 1 per (tenant, year)
# ============================================================
class PutWorkingDayPolicy(BaseModel):
    academic_year_id: str
    working_days: list[str]
    half_days: list[str] = Field(default_factory=list)
    weekly_off: list[str] = Field(default_factory=list)
    notes: str | None = None


@router.get("/working-day-policy")
async def get_working_days(academic_year_id: str, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    db = get_db()
    d = await db.working_day_policies.find_one({"tenant_id": user["tenant_id"], "academic_year_id": academic_year_id})
    if not d: return {"academic_year_id": academic_year_id, "working_days": ["mon","tue","wed","thu","fri"], "half_days": [], "weekly_off": ["sat","sun"], "notes": None, "id": None}
    return _out(d)


@router.put("/working-day-policy")
async def put_working_days(payload: PutWorkingDayPolicy, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_CALENDAR_MANAGE))):
    db = get_db()
    await _assert_year_editable(db, user["tenant_id"], payload.academic_year_id)
    for d in [*payload.working_days, *payload.half_days, *payload.weekly_off]:
        if d not in WEEKDAYS:
            raise HTTPException(status_code=400, detail=f"Unknown weekday: {d}")
    overlap = set(payload.working_days) & set(payload.weekly_off)
    if overlap:
        raise HTTPException(status_code=409, detail={"code": "weekday_conflict", "message": f"Days both working & weekly-off: {sorted(overlap)}"})
    if not set(payload.half_days).issubset(set(payload.working_days)):
        raise HTTPException(status_code=400, detail="half_days must be a subset of working_days")
    existing = await db.working_day_policies.find_one({"tenant_id": user["tenant_id"], "academic_year_id": payload.academic_year_id})
    payload_dict = payload.model_dump()
    payload_dict["updated_at"] = _now_iso()
    if existing:
        await db.working_day_policies.update_one({"_id": existing["_id"]}, {"$set": payload_dict})
    else:
        doc = WorkingDayPolicy(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
        await db.working_day_policies.insert_one(doc)
    await log_event(action="academic.working_days.set", resource="working_day_policy",
                    resource_id=payload.academic_year_id, tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value=payload_dict)
    return _out(await db.working_day_policies.find_one({"tenant_id": user["tenant_id"], "academic_year_id": payload.academic_year_id}))


# ============================================================
# Holidays
# ============================================================
class CreateHoliday(BaseModel):
    academic_year_id: str
    name: str = Field(min_length=1, max_length=200)
    start_date: str
    end_date: str
    category: str = "public"
    is_recurring: bool = False
    notes: str | None = None


class UpdateHoliday(BaseModel):
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    category: str | None = None
    is_recurring: bool | None = None
    notes: str | None = None


@router.get("/holidays")
async def list_holidays(academic_year_id: str | None = None, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    q: dict = {"tenant_id": user["tenant_id"]}
    if academic_year_id: q["academic_year_id"] = academic_year_id
    docs = await get_db().holidays.find(q).sort("start_date", 1).to_list(500)
    return [_out(d) for d in docs]


@router.post("/holidays", status_code=201)
async def create_holiday(payload: CreateHoliday, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_CALENDAR_MANAGE))):
    db = get_db()
    await _assert_year_editable(db, user["tenant_id"], payload.academic_year_id)
    if payload.start_date > payload.end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    doc = Holiday(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.holidays.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="academic.holiday.create", resource="holiday",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"name": payload.name})
    return _out(doc)


@router.patch("/holidays/{hid}")
async def update_holiday(hid: str, payload: UpdateHoliday, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_CALENDAR_MANAGE))):
    db = get_db()
    old = await db.holidays.find_one({"_id": _oid(hid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Holiday not found")
    await _assert_year_editable(db, user["tenant_id"], old["academic_year_id"])
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    if updates.get("start_date") and updates.get("end_date") and updates["start_date"] > updates["end_date"]:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    updates["updated_at"] = _now_iso()
    await db.holidays.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="academic.holiday.update", resource="holiday",
                    resource_id=hid, tenant_id=user["tenant_id"], actor=user, request=request,
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(await db.holidays.find_one({"_id": old["_id"]}))


@router.delete("/holidays/{hid}")
async def delete_holiday(hid: str, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_CALENDAR_MANAGE))):
    db = get_db()
    old = await db.holidays.find_one({"_id": _oid(hid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Holiday not found")
    await _assert_year_editable(db, user["tenant_id"], old["academic_year_id"])
    await db.holidays.delete_one({"_id": old["_id"]})
    await log_event(action="academic.holiday.delete", resource="holiday",
                    resource_id=hid, tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Teacher assignments
# ============================================================
class CreateTeacherAssignment(BaseModel):
    academic_year_id: str
    teacher_user_id: str
    class_id: str
    section_id: str | None = None
    subject_id: str | None = None
    is_class_teacher: bool = False
    weekly_periods: int | None = None
    notes: str | None = None


class UpdateTeacherAssignment(BaseModel):
    section_id: str | None = None
    subject_id: str | None = None
    is_class_teacher: bool | None = None
    weekly_periods: int | None = None
    notes: str | None = None


@router.get("/teacher-assignments")
async def list_teacher_assignments(
    academic_year_id: str | None = None, class_id: str | None = None,
    section_id: str | None = None, teacher_user_id: str | None = None,
    user: dict = Depends(require_permission(P_ACADEMIC_VIEW)),
):
    q: dict = {"tenant_id": user["tenant_id"]}
    if academic_year_id: q["academic_year_id"] = academic_year_id
    if class_id: q["class_id"] = class_id
    if section_id: q["section_id"] = section_id
    if teacher_user_id: q["teacher_user_id"] = teacher_user_id
    docs = await get_db().teacher_assignments.find(q).sort("created_at", -1).to_list(2000)
    return [_out(d) for d in docs]


@router.post("/teacher-assignments", status_code=201)
async def create_teacher_assignment(payload: CreateTeacherAssignment, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_ASSIGN_MANAGE))):
    db = get_db()
    await _assert_year_editable(db, user["tenant_id"], payload.academic_year_id)
    teacher = await db.users.find_one({"_id": _oid(payload.teacher_user_id), "tenant_id": user["tenant_id"]})
    if not teacher or teacher.get("role") not in {"teacher", "class_teacher"}:
        raise HTTPException(status_code=400, detail="teacher_user_id must reference a user with role teacher/class_teacher")
    klass = await db.academic_classes.find_one({"_id": _oid(payload.class_id), "tenant_id": user["tenant_id"]})
    if not klass or klass["academic_year_id"] != payload.academic_year_id:
        raise HTTPException(status_code=400, detail="class_id must belong to the given academic_year_id")
    if payload.section_id:
        sec = await db.academic_sections.find_one({"_id": _oid(payload.section_id), "tenant_id": user["tenant_id"]})
        if not sec or sec["class_id"] != payload.class_id:
            raise HTTPException(status_code=400, detail="section_id must belong to the given class_id")
    if payload.subject_id and not await db.subjects.find_one({"_id": _oid(payload.subject_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=400, detail="subject_id not found")
    # Class-teacher uniqueness — exactly one class-teacher per section per year.
    if payload.is_class_teacher:
        if not payload.section_id:
            raise HTTPException(status_code=400, detail="is_class_teacher requires section_id")
        clash = await db.teacher_assignments.find_one({
            "tenant_id": user["tenant_id"], "academic_year_id": payload.academic_year_id,
            "class_id": payload.class_id, "section_id": payload.section_id, "is_class_teacher": True,
        })
        if clash:
            raise HTTPException(status_code=409, detail={"code": "class_teacher_exists", "message": "This section already has a class-teacher assignment"})
    dup = await db.teacher_assignments.find_one({
        "tenant_id": user["tenant_id"], "academic_year_id": payload.academic_year_id,
        "teacher_user_id": payload.teacher_user_id, "class_id": payload.class_id,
        "section_id": payload.section_id, "subject_id": payload.subject_id,
    })
    if dup:
        raise HTTPException(status_code=409, detail={"code": "duplicate_assignment", "message": "Identical assignment already exists"})
    doc = TeacherAssignment(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.teacher_assignments.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="academic.assignment.create", resource="teacher_assignment",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={
                        "teacher_user_id": payload.teacher_user_id,
                        "class_id": payload.class_id, "section_id": payload.section_id,
                        "subject_id": payload.subject_id,
                    })
    return _out(doc)


@router.patch("/teacher-assignments/{aid}")
async def update_teacher_assignment(aid: str, payload: UpdateTeacherAssignment, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_ASSIGN_MANAGE))):
    db = get_db()
    old = await db.teacher_assignments.find_one({"_id": _oid(aid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Assignment not found")
    await _assert_year_editable(db, user["tenant_id"], old["academic_year_id"])
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = _now_iso()
    await db.teacher_assignments.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="academic.assignment.update", resource="teacher_assignment",
                    resource_id=aid, tenant_id=user["tenant_id"], actor=user, request=request,
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(await db.teacher_assignments.find_one({"_id": old["_id"]}))


@router.delete("/teacher-assignments/{aid}")
async def delete_teacher_assignment(aid: str, request: Request, user: dict = Depends(require_permission(P_ACADEMIC_ASSIGN_MANAGE))):
    db = get_db()
    old = await db.teacher_assignments.find_one({"_id": _oid(aid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Assignment not found")
    await _assert_year_editable(db, user["tenant_id"], old["academic_year_id"])
    await db.teacher_assignments.delete_one({"_id": old["_id"]})
    await log_event(action="academic.assignment.delete", resource="teacher_assignment",
                    resource_id=aid, tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Overview — quick dashboard rollup for a year
# ============================================================
@router.get("/overview/{yid}")
async def academic_overview(yid: str, user: dict = Depends(require_permission(P_ACADEMIC_VIEW))):
    db = get_db()
    y = await _get_year(db, user["tenant_id"], yid)
    tid = user["tenant_id"]
    counts = {
        "classes": await db.academic_classes.count_documents({"tenant_id": tid, "academic_year_id": yid}),
        "sections": await db.academic_sections.count_documents({"tenant_id": tid, "academic_year_id": yid}),
        "subjects": await db.subjects.count_documents({"tenant_id": tid}),
        "rooms": await db.rooms.count_documents({"tenant_id": tid}),
        "bell_schedules": await db.bell_schedules.count_documents({"tenant_id": tid, "academic_year_id": yid}),
        "holidays": await db.holidays.count_documents({"tenant_id": tid, "academic_year_id": yid}),
        "teacher_assignments": await db.teacher_assignments.count_documents({"tenant_id": tid, "academic_year_id": yid}),
        "students_snapshot": await db.students.count_documents({"tenant_id": tid, "academic_year": y["name"]}),
    }
    return {"year": _out(y), "counts": counts, "statuses": ACADEMIC_YEAR_STATUSES}
