"""Timetable Engine + Proxy Scheduling routes — Prompt 7.

Endpoints
---------
Master timetable:
  GET    /school/timetable/slots                     (list; filters: year, class, section, weekday, teacher)
  POST   /school/timetable/slots                     (create one slot; conflict-checked)
  POST   /school/timetable/slots/bulk-upsert         (bulk overwrite a section's grid)
  PATCH  /school/timetable/slots/{id}                (edit)
  DELETE /school/timetable/slots/{id}
  GET    /school/timetable/grid                      (section's grid view)
  GET    /school/timetable/teacher/{user_id}/weekly  (teacher's weekly schedule)
  POST   /school/timetable/validate                  (dry-run conflict check for a slot payload)
  GET    /school/timetable/sections                  (publish-status list)
  POST   /school/timetable/sections/publish          (publish a section)
  POST   /school/timetable/sections/lock             (lock/unlock)
  GET    /school/timetable/for-date                  (daily view with substitution overlay)

Proxy / Substitute:
  GET    /school/proxy/config                        + PUT
  GET    /school/proxy/absences                      (presumed-absent teachers for a date)
  GET    /school/proxy/recommendations               (ranked candidates per affected period)
  GET    /school/proxy/substitutions                 (list by date / teacher)
  POST   /school/proxy/substitutions                 (admin creates a substitution record)
  POST   /school/proxy/substitutions/{id}/approve
  POST   /school/proxy/substitutions/{id}/reject
  POST   /school/proxy/substitutions/{id}/cancel
"""
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.core.deps import require_permission
from app.core.permissions import (
    P_PROXY_APPROVE, P_PROXY_CONFIG, P_PROXY_MANAGE, P_PROXY_VIEW,
    P_TIMETABLE_MANAGE, P_TIMETABLE_PUBLISH, P_TIMETABLE_VIEW,
    permissions_for,
)
from app.models.academic import WEEKDAYS
from app.models.timetable import (
    ProxyConfig, Substitution, TimetableSectionMeta, TimetableSlot,
)
from app.services.alert_service import create_alert
from app.services.audit_service import log_event

router = APIRouter(prefix="/school", tags=["timetable"])


# ============================================================
# Helpers
# ============================================================
def _oid(v: str) -> ObjectId:
    try: return ObjectId(v)
    except InvalidId: raise HTTPException(status_code=404, detail="Not found")


def _out(d: dict) -> dict:
    d = dict(d); d["id"] = str(d.pop("_id")); return d


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


_WEEKDAY_FROM_DATE = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _weekday_of(iso_date: str) -> str:
    """Return mon/tue/.../sun for an ISO date string."""
    try:
        return _WEEKDAY_FROM_DATE[datetime.strptime(iso_date, "%Y-%m-%d").weekday()]
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be ISO YYYY-MM-DD")


async def _get_year(db, tid: str, yid: str) -> dict:
    y = await db.academic_years.find_one({"_id": _oid(yid), "tenant_id": tid})
    if not y: raise HTTPException(status_code=404, detail="Academic year not found")
    return y


async def _assert_year_editable(db, tid: str, yid: str) -> dict:
    y = await _get_year(db, tid, yid)
    if y.get("status") == "archived":
        raise HTTPException(status_code=409, detail={"code": "year_archived", "message": "Academic year is archived and read-only"})
    return y


async def _get_bell(db, tid: str, bid: str) -> dict:
    b = await db.bell_schedules.find_one({"_id": _oid(bid), "tenant_id": tid})
    if not b: raise HTTPException(status_code=404, detail="Bell schedule not found")
    return b


async def _get_working_policy(db, tid: str, yid: str) -> dict:
    pol = await db.working_day_policies.find_one({"tenant_id": tid, "academic_year_id": yid})
    if pol: return pol
    return {"working_days": ["mon","tue","wed","thu","fri"], "half_days": [], "weekly_off": ["sat","sun"]}


async def _validate_slot_fks(db, tid: str, p: dict) -> dict:
    """Validate FKs and return resolved docs.  Mutates p['teacher_employee_id']."""
    yid = p["academic_year_id"]
    klass = await db.academic_classes.find_one({"_id": _oid(p["class_id"]), "tenant_id": tid})
    if not klass or klass["academic_year_id"] != yid:
        raise HTTPException(status_code=400, detail="class_id must belong to academic_year_id")
    section = await db.academic_sections.find_one({"_id": _oid(p["section_id"]), "tenant_id": tid})
    if not section or section["class_id"] != p["class_id"]:
        raise HTTPException(status_code=400, detail="section_id must belong to class_id")
    bell = await _get_bell(db, tid, p["bell_schedule_id"])
    if bell["academic_year_id"] != yid:
        raise HTTPException(status_code=400, detail="bell_schedule_id must belong to academic_year_id")
    pol = await _get_working_policy(db, tid, yid)
    if p["weekday"] not in WEEKDAYS:
        raise HTTPException(status_code=400, detail=f"Unknown weekday")
    if p["weekday"] in pol.get("weekly_off", []):
        raise HTTPException(status_code=409, detail={"code": "weekly_off_day", "message": f"{p['weekday']} is a weekly off day"})
    if p["weekday"] not in pol.get("working_days", WEEKDAYS):
        raise HTTPException(status_code=409, detail={"code": "non_working_day", "message": f"{p['weekday']} is not a working day"})
    periods = bell.get("periods") or []
    period_nos = {int(x.get("period_no")) for x in periods if isinstance(x.get("period_no"), int)}
    if p["period_no"] not in period_nos:
        raise HTTPException(status_code=400, detail=f"period_no {p['period_no']} not in bell schedule")
    bell_period = next((bp for bp in periods if bp.get("period_no") == p["period_no"]), None)
    if bell_period and bell_period.get("is_break"):
        raise HTTPException(status_code=409, detail={"code": "period_is_break", "message": "Cannot assign a class to a break period"})
    if p.get("subject_id"):
        if not await db.subjects.find_one({"_id": _oid(p["subject_id"]), "tenant_id": tid}):
            raise HTTPException(status_code=400, detail="subject_id not found")
    teacher_employee_id = None
    if p.get("teacher_user_id"):
        u = await db.users.find_one({"_id": _oid(p["teacher_user_id"]), "tenant_id": tid})
        if not u or u.get("role") not in {"teacher", "class_teacher"}:
            raise HTTPException(status_code=400, detail="teacher_user_id must reference a teacher/class_teacher")
        emp = await db.employees.find_one({"tenant_id": tid, "user_id": p["teacher_user_id"]})
        if emp: teacher_employee_id = str(emp["_id"])
    if p.get("room_id"):
        if not await db.rooms.find_one({"_id": _oid(p["room_id"]), "tenant_id": tid}):
            raise HTTPException(status_code=400, detail="room_id not found")
    return {"klass": klass, "section": section, "bell": bell, "teacher_employee_id": teacher_employee_id}


async def _detect_conflicts(db, tid: str, p: dict, exclude_id: str | None = None) -> list[dict]:
    """Return list of conflict descriptors for a candidate slot."""
    conflicts: list[dict] = []
    base = {
        "tenant_id": tid, "academic_year_id": p["academic_year_id"],
        "weekday": p["weekday"], "period_no": p["period_no"],
    }
    excl = {"_id": {"$ne": _oid(exclude_id)}} if exclude_id else {}
    # Teacher double-book
    if p.get("teacher_user_id"):
        clash = await db.timetable_slots.find_one({**base, "teacher_user_id": p["teacher_user_id"], **excl})
        if clash:
            conflicts.append({
                "code": "teacher_double_book",
                "message": "Teacher already assigned to another section at this period",
                "slot_id": str(clash["_id"]),
                "class_id": clash.get("class_id"),
                "section_id": clash.get("section_id"),
            })
    # Room double-book
    if p.get("room_id"):
        clash = await db.timetable_slots.find_one({**base, "room_id": p["room_id"], **excl})
        if clash:
            conflicts.append({
                "code": "room_double_book",
                "message": "Room already booked at this period",
                "slot_id": str(clash["_id"]),
                "class_id": clash.get("class_id"),
                "section_id": clash.get("section_id"),
            })
    # Section-slot uniqueness
    clash = await db.timetable_slots.find_one({
        **base, "section_id": p["section_id"], **excl,
    })
    if clash:
        conflicts.append({
            "code": "section_slot_taken",
            "message": "Section already has a slot at this weekday/period",
            "slot_id": str(clash["_id"]),
        })
    return conflicts


async def _get_or_create_section_meta(db, tid: str, p: dict) -> dict:
    doc = await db.timetable_section_meta.find_one({
        "tenant_id": tid, "academic_year_id": p["academic_year_id"],
        "section_id": p["section_id"],
    })
    if doc: return doc
    meta = TimetableSectionMeta(
        tenant_id=tid, academic_year_id=p["academic_year_id"],
        class_id=p["class_id"], section_id=p["section_id"],
        bell_schedule_id=p["bell_schedule_id"], status="draft",
    ).to_mongo()
    res = await db.timetable_section_meta.insert_one(meta); meta["_id"] = res.inserted_id
    return meta


async def _assert_section_editable(db, tid: str, section_id: str) -> dict | None:
    """Reject edits when the section's timetable is locked."""
    meta = await db.timetable_section_meta.find_one({"tenant_id": tid, "section_id": section_id})
    if meta and meta.get("locked"):
        raise HTTPException(status_code=409, detail={"code": "timetable_locked", "message": "Section timetable is locked"})
    return meta


# ============================================================
# Pydantic payloads
# ============================================================
class SlotIn(BaseModel):
    academic_year_id: str
    class_id: str
    section_id: str
    bell_schedule_id: str
    weekday: str
    period_no: int = Field(ge=1)
    subject_id: str | None = None
    teacher_user_id: str | None = None
    room_id: str | None = None
    label: str | None = None
    notes: str | None = None


class SlotUpdate(BaseModel):
    subject_id: str | None = None
    teacher_user_id: str | None = None
    room_id: str | None = None
    label: str | None = None
    notes: str | None = None
    clear: list[str] = Field(default_factory=list)   # explicit "unset" list (subject_id/teacher_user_id/room_id/label/notes)


class BulkSlots(BaseModel):
    academic_year_id: str
    class_id: str
    section_id: str
    bell_schedule_id: str
    slots: list[SlotIn] = Field(default_factory=list)
    replace: bool = True    # delete existing non-listed cells for the section


class PublishSection(BaseModel):
    academic_year_id: str
    section_id: str


class LockToggle(BaseModel):
    academic_year_id: str
    section_id: str
    locked: bool


# ============================================================
# Slot CRUD
# ============================================================
@router.get("/timetable/slots")
async def list_slots(
    academic_year_id: str,
    class_id: str | None = None,
    section_id: str | None = None,
    weekday: str | None = None,
    teacher_user_id: str | None = None,
    room_id: str | None = None,
    user: dict = Depends(require_permission(P_TIMETABLE_VIEW)),
):
    db = get_db()
    q: dict = {"tenant_id": user["tenant_id"], "academic_year_id": academic_year_id}
    if class_id: q["class_id"] = class_id
    if section_id: q["section_id"] = section_id
    if weekday: q["weekday"] = weekday
    if teacher_user_id: q["teacher_user_id"] = teacher_user_id
    if room_id: q["room_id"] = room_id
    docs = await db.timetable_slots.find(q).sort([("weekday", 1), ("period_no", 1)]).to_list(5000)
    return [_out(d) for d in docs]


@router.post("/timetable/slots", status_code=201)
async def create_slot(payload: SlotIn, request: Request, user: dict = Depends(require_permission(P_TIMETABLE_MANAGE))):
    db = get_db(); tid = user["tenant_id"]
    p = payload.model_dump()
    await _assert_year_editable(db, tid, p["academic_year_id"])
    await _assert_section_editable(db, tid, p["section_id"])
    v = await _validate_slot_fks(db, tid, p)
    conflicts = await _detect_conflicts(db, tid, p)
    if conflicts:
        raise HTTPException(status_code=409, detail={"code": "timetable_conflict", "message": "Slot conflicts detected", "conflicts": conflicts})
    doc = TimetableSlot(
        tenant_id=tid, **p, teacher_employee_id=v["teacher_employee_id"],
    ).to_mongo()
    res = await db.timetable_slots.insert_one(doc); doc["_id"] = res.inserted_id
    await _get_or_create_section_meta(db, tid, p)
    await log_event(action="timetable.slot.create", resource="timetable_slot",
                    resource_id=str(res.inserted_id), tenant_id=tid,
                    actor=user, request=request, new_value={
                        "section_id": p["section_id"], "weekday": p["weekday"], "period_no": p["period_no"],
                    })
    return _out(doc)


@router.post("/timetable/slots/bulk-upsert")
async def bulk_upsert_slots(payload: BulkSlots, request: Request, user: dict = Depends(require_permission(P_TIMETABLE_MANAGE))):
    """Overwrite a section's weekly grid in one call.  Non-destructive to
    other sections.  Validates every slot before writing anything."""
    db = get_db(); tid = user["tenant_id"]
    await _assert_year_editable(db, tid, payload.academic_year_id)
    await _assert_section_editable(db, tid, payload.section_id)
    await _get_bell(db, tid, payload.bell_schedule_id)
    # Normalise and validate every slot against this payload's section first.
    prepared: list[dict] = []
    for sl in payload.slots:
        p = sl.model_dump()
        p["academic_year_id"] = payload.academic_year_id
        p["class_id"] = payload.class_id
        p["section_id"] = payload.section_id
        p["bell_schedule_id"] = payload.bell_schedule_id
        v = await _validate_slot_fks(db, tid, p)
        p["teacher_employee_id"] = v["teacher_employee_id"]
        prepared.append(p)

    # In-payload uniqueness: no two slots on the same (weekday, period_no)
    seen = set()
    for p in prepared:
        key = (p["weekday"], p["period_no"])
        if key in seen:
            raise HTTPException(status_code=409, detail={"code": "duplicate_cell", "message": f"Payload has two entries for {key}"})
        seen.add(key)

    # Cross-section conflicts (teacher/room double-book), ignore same-section cells.
    for p in prepared:
        base = {
            "tenant_id": tid, "academic_year_id": payload.academic_year_id,
            "weekday": p["weekday"], "period_no": p["period_no"],
            "section_id": {"$ne": payload.section_id},
        }
        if p.get("teacher_user_id"):
            clash = await db.timetable_slots.find_one({**base, "teacher_user_id": p["teacher_user_id"]})
            if clash:
                raise HTTPException(status_code=409, detail={
                    "code": "teacher_double_book",
                    "message": f"Teacher clash at {p['weekday']} P{p['period_no']}",
                    "slot_id": str(clash["_id"]),
                })
        if p.get("room_id"):
            clash = await db.timetable_slots.find_one({**base, "room_id": p["room_id"]})
            if clash:
                raise HTTPException(status_code=409, detail={
                    "code": "room_double_book",
                    "message": f"Room clash at {p['weekday']} P{p['period_no']}",
                    "slot_id": str(clash["_id"]),
                })

    # Replace strategy: wipe current section entries then insert.
    if payload.replace:
        await db.timetable_slots.delete_many({
            "tenant_id": tid, "academic_year_id": payload.academic_year_id,
            "section_id": payload.section_id,
        })
        if prepared:
            docs = [TimetableSlot(tenant_id=tid, **p).to_mongo() for p in prepared]
            await db.timetable_slots.insert_many(docs)
    else:
        # Upsert per cell
        for p in prepared:
            await db.timetable_slots.update_one(
                {
                    "tenant_id": tid, "academic_year_id": payload.academic_year_id,
                    "section_id": payload.section_id,
                    "weekday": p["weekday"], "period_no": p["period_no"],
                },
                {"$set": {**p, "tenant_id": tid, "updated_at": _now()},
                 "$setOnInsert": {"created_at": _now()}},
                upsert=True,
            )

    await _get_or_create_section_meta(db, tid, {
        "academic_year_id": payload.academic_year_id, "class_id": payload.class_id,
        "section_id": payload.section_id, "bell_schedule_id": payload.bell_schedule_id,
    })
    await log_event(action="timetable.slot.bulk_upsert", resource="timetable_slot",
                    resource_id=payload.section_id, tenant_id=tid,
                    actor=user, request=request, new_value={"count": len(prepared), "replace": payload.replace})
    docs = await db.timetable_slots.find({
        "tenant_id": tid, "academic_year_id": payload.academic_year_id,
        "section_id": payload.section_id,
    }).sort([("weekday", 1), ("period_no", 1)]).to_list(1000)
    return {"ok": True, "count": len(docs), "slots": [_out(d) for d in docs]}


@router.patch("/timetable/slots/{sid}")
async def update_slot(sid: str, payload: SlotUpdate, request: Request, user: dict = Depends(require_permission(P_TIMETABLE_MANAGE))):
    db = get_db(); tid = user["tenant_id"]
    old = await db.timetable_slots.find_one({"_id": _oid(sid), "tenant_id": tid})
    if not old: raise HTTPException(status_code=404, detail="Slot not found")
    await _assert_year_editable(db, tid, old["academic_year_id"])
    await _assert_section_editable(db, tid, old["section_id"])
    updates = payload.model_dump(exclude_none=True)
    clear = updates.pop("clear", [])
    # Compose candidate
    candidate = dict(old)
    candidate.update(updates)
    for k in clear:
        if k in {"subject_id", "teacher_user_id", "room_id", "label", "notes"}:
            candidate[k] = None
    # Resolve teacher_employee_id if teacher changed
    teacher_employee_id = old.get("teacher_employee_id")
    if "teacher_user_id" in updates or "teacher_user_id" in clear:
        teacher_employee_id = None
        if candidate.get("teacher_user_id"):
            u = await db.users.find_one({"_id": _oid(candidate["teacher_user_id"]), "tenant_id": tid})
            if not u or u.get("role") not in {"teacher", "class_teacher"}:
                raise HTTPException(status_code=400, detail="teacher_user_id must reference a teacher")
            emp = await db.employees.find_one({"tenant_id": tid, "user_id": candidate["teacher_user_id"]})
            teacher_employee_id = str(emp["_id"]) if emp else None
    if candidate.get("subject_id"):
        if not await db.subjects.find_one({"_id": _oid(candidate["subject_id"]), "tenant_id": tid}):
            raise HTTPException(status_code=400, detail="subject_id not found")
    if candidate.get("room_id"):
        if not await db.rooms.find_one({"_id": _oid(candidate["room_id"]), "tenant_id": tid}):
            raise HTTPException(status_code=400, detail="room_id not found")
    conflicts = await _detect_conflicts(db, tid, {
        "academic_year_id": old["academic_year_id"], "section_id": old["section_id"],
        "weekday": old["weekday"], "period_no": old["period_no"],
        "teacher_user_id": candidate.get("teacher_user_id"),
        "room_id": candidate.get("room_id"),
    }, exclude_id=sid)
    # section_slot_taken is impossible here (same row); filter it.
    conflicts = [c for c in conflicts if c["code"] != "section_slot_taken"]
    if conflicts:
        raise HTTPException(status_code=409, detail={"code": "timetable_conflict", "message": "Slot conflicts detected", "conflicts": conflicts})
    patch = {**updates}
    for k in clear:
        patch[k] = None
    patch["teacher_employee_id"] = teacher_employee_id
    patch["updated_at"] = _now()
    await db.timetable_slots.update_one({"_id": old["_id"]}, {"$set": patch})
    await log_event(action="timetable.slot.update", resource="timetable_slot",
                    resource_id=sid, tenant_id=tid, actor=user, request=request,
                    new_value={k: v for k, v in patch.items() if k != "updated_at"})
    return _out(await db.timetable_slots.find_one({"_id": old["_id"]}))


@router.delete("/timetable/slots/{sid}")
async def delete_slot(sid: str, request: Request, user: dict = Depends(require_permission(P_TIMETABLE_MANAGE))):
    db = get_db(); tid = user["tenant_id"]
    old = await db.timetable_slots.find_one({"_id": _oid(sid), "tenant_id": tid})
    if not old: raise HTTPException(status_code=404, detail="Slot not found")
    await _assert_year_editable(db, tid, old["academic_year_id"])
    await _assert_section_editable(db, tid, old["section_id"])
    await db.timetable_slots.delete_one({"_id": old["_id"]})
    await log_event(action="timetable.slot.delete", resource="timetable_slot",
                    resource_id=sid, tenant_id=tid, actor=user, request=request)
    return {"ok": True}


@router.post("/timetable/validate")
async def validate_slot(payload: SlotIn, user: dict = Depends(require_permission(P_TIMETABLE_VIEW))):
    db = get_db(); tid = user["tenant_id"]
    p = payload.model_dump()
    await _validate_slot_fks(db, tid, p)
    conflicts = await _detect_conflicts(db, tid, p)
    return {"ok": not conflicts, "conflicts": conflicts}


# ============================================================
# Grid, teacher weekly, publish/lock
# ============================================================
@router.get("/timetable/grid")
async def get_grid(
    academic_year_id: str, section_id: str,
    user: dict = Depends(require_permission(P_TIMETABLE_VIEW)),
):
    db = get_db(); tid = user["tenant_id"]
    sec = await db.academic_sections.find_one({"_id": _oid(section_id), "tenant_id": tid})
    if not sec: raise HTTPException(status_code=404, detail="Section not found")
    meta = await db.timetable_section_meta.find_one({
        "tenant_id": tid, "academic_year_id": academic_year_id, "section_id": section_id,
    })
    bell_id = meta.get("bell_schedule_id") if meta else None
    if not bell_id:
        default = await db.bell_schedules.find_one({
            "tenant_id": tid, "academic_year_id": academic_year_id, "is_default": True,
        })
        bell_id = str(default["_id"]) if default else None
    bell = None
    if bell_id:
        bell_doc = await db.bell_schedules.find_one({"_id": _oid(bell_id), "tenant_id": tid})
        if bell_doc: bell = _out(bell_doc)
    pol = await _get_working_policy(db, tid, academic_year_id)
    slots = await db.timetable_slots.find({
        "tenant_id": tid, "academic_year_id": academic_year_id, "section_id": section_id,
    }).sort([("weekday", 1), ("period_no", 1)]).to_list(500)
    return {
        "section": {"id": str(sec["_id"]), "name": sec.get("name"), "class_id": sec.get("class_id"), "room_id": sec.get("room_id")},
        "meta": _out(meta) if meta else None,
        "bell_schedule": bell,
        "working_days": pol.get("working_days", []),
        "weekly_off": pol.get("weekly_off", []),
        "slots": [_out(s) for s in slots],
    }


@router.get("/timetable/teacher/{tu}/weekly")
async def teacher_weekly(tu: str, academic_year_id: str, user: dict = Depends(require_permission(P_TIMETABLE_VIEW))):
    db = get_db(); tid = user["tenant_id"]
    slots = await db.timetable_slots.find({
        "tenant_id": tid, "academic_year_id": academic_year_id, "teacher_user_id": tu,
    }).sort([("weekday", 1), ("period_no", 1)]).to_list(500)
    return {"teacher_user_id": tu, "slots": [_out(s) for s in slots]}


@router.get("/timetable/sections")
async def list_section_meta(academic_year_id: str, user: dict = Depends(require_permission(P_TIMETABLE_VIEW))):
    db = get_db()
    docs = await db.timetable_section_meta.find({
        "tenant_id": user["tenant_id"], "academic_year_id": academic_year_id,
    }).sort("updated_at", -1).to_list(500)
    return [_out(d) for d in docs]


@router.post("/timetable/sections/publish")
async def publish_section(payload: PublishSection, request: Request, user: dict = Depends(require_permission(P_TIMETABLE_PUBLISH))):
    db = get_db(); tid = user["tenant_id"]
    await _assert_year_editable(db, tid, payload.academic_year_id)
    meta = await db.timetable_section_meta.find_one({
        "tenant_id": tid, "academic_year_id": payload.academic_year_id, "section_id": payload.section_id,
    })
    if not meta:
        raise HTTPException(status_code=404, detail="Section timetable not initialised — add slots first")
    count = await db.timetable_slots.count_documents({
        "tenant_id": tid, "academic_year_id": payload.academic_year_id, "section_id": payload.section_id,
    })
    if count == 0:
        raise HTTPException(status_code=409, detail={"code": "empty_timetable", "message": "No slots to publish"})
    now = _now()
    await db.timetable_section_meta.update_one({"_id": meta["_id"]}, {"$set": {
        "status": "published", "published_at": now, "published_by_user_id": user.get("id"),
        "updated_at": now,
    }})
    await log_event(action="timetable.section.publish", resource="timetable_section_meta",
                    resource_id=str(meta["_id"]), tenant_id=tid, actor=user, request=request,
                    new_value={"section_id": payload.section_id})
    return _out(await db.timetable_section_meta.find_one({"_id": meta["_id"]}))


@router.post("/timetable/sections/lock")
async def lock_section(payload: LockToggle, request: Request, user: dict = Depends(require_permission(P_TIMETABLE_PUBLISH))):
    db = get_db(); tid = user["tenant_id"]
    meta = await db.timetable_section_meta.find_one({
        "tenant_id": tid, "academic_year_id": payload.academic_year_id, "section_id": payload.section_id,
    })
    if not meta: raise HTTPException(status_code=404, detail="Section timetable not initialised")
    await db.timetable_section_meta.update_one({"_id": meta["_id"]}, {"$set": {"locked": payload.locked, "updated_at": _now()}})
    await log_event(action="timetable.section.lock" if payload.locked else "timetable.section.unlock",
                    resource="timetable_section_meta", resource_id=str(meta["_id"]),
                    tenant_id=tid, actor=user, request=request, new_value={"locked": payload.locked})
    return _out(await db.timetable_section_meta.find_one({"_id": meta["_id"]}))


# ============================================================
# For-date view (master + substitution overlay)
# ============================================================
@router.get("/timetable/for-date")
async def timetable_for_date(
    date: str, academic_year_id: str,
    section_id: str | None = None,
    teacher_user_id: str | None = None,
    user: dict = Depends(require_permission(P_TIMETABLE_VIEW)),
):
    db = get_db(); tid = user["tenant_id"]
    wd = _weekday_of(date)
    q: dict = {"tenant_id": tid, "academic_year_id": academic_year_id, "weekday": wd}
    if section_id: q["section_id"] = section_id
    if teacher_user_id: q["teacher_user_id"] = teacher_user_id
    slots = await db.timetable_slots.find(q).sort("period_no", 1).to_list(500)
    sub_q = {"tenant_id": tid, "date": date, "status": "approved"}
    if section_id: sub_q["section_id"] = section_id
    subs = await db.substitutions.find(sub_q).to_list(500)
    # Index subs by (section_id, period_no)
    sub_idx = {(s.get("section_id"), s.get("period_no")): s for s in subs}
    rows: list[dict] = []
    for s in slots:
        key = (s.get("section_id"), s.get("period_no"))
        sub = sub_idx.get(key)
        row = _out(s); row["substitution"] = _out(sub) if sub else None
        rows.append(row)
    # Also include subs that have no master slot (edge case)
    for s in subs:
        key = (s.get("section_id"), s.get("period_no"))
        if not any((r.get("section_id") == key[0] and r.get("period_no") == key[1]) for r in rows):
            rows.append({"substitution": _out(s), "section_id": key[0], "period_no": key[1], "weekday": wd})
    return {"date": date, "weekday": wd, "rows": rows}


# ============================================================
# Proxy — config
# ============================================================
async def _get_proxy_config(db, tid: str) -> dict:
    cfg = await db.proxy_configs.find_one({"tenant_id": tid})
    if cfg: return cfg
    doc = ProxyConfig(tenant_id=tid).to_mongo()
    res = await db.proxy_configs.insert_one(doc); doc["_id"] = res.inserted_id
    return doc


class UpdateProxyConfig(BaseModel):
    cutoff_time: str | None = None
    attendance_grace_minutes: int | None = None
    use_leave_source: bool | None = None
    use_attendance_source: bool | None = None
    auto_run_enabled: bool | None = None
    auto_run_time: str | None = None
    require_subject_match: bool | None = None
    prefer_same_grade: bool | None = None
    max_proxy_per_day_per_teacher: int | None = None
    notify_substitute: bool | None = None
    notify_class_teacher: bool | None = None
    notify_admin: bool | None = None
    notes: str | None = None


@router.get("/proxy/config")
async def get_proxy_config(user: dict = Depends(require_permission(P_PROXY_VIEW))):
    return _out(await _get_proxy_config(get_db(), user["tenant_id"]))


@router.put("/proxy/config")
async def update_proxy_config(payload: UpdateProxyConfig, request: Request, user: dict = Depends(require_permission(P_PROXY_CONFIG))):
    db = get_db(); tid = user["tenant_id"]
    cfg = await _get_proxy_config(db, tid)
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = _now()
    await db.proxy_configs.update_one({"_id": cfg["_id"]}, {"$set": updates})
    await log_event(action="proxy.config.update", resource="proxy_config",
                    resource_id=str(cfg["_id"]), tenant_id=tid, actor=user, request=request,
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(await db.proxy_configs.find_one({"_id": cfg["_id"]}))


# ============================================================
# Proxy — absence detection
# ============================================================
def _hhmm_now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M")


async def _detect_absences(db, tid: str, date: str, academic_year_id: str) -> dict:
    """Return the set of teacher_user_ids presumed absent on `date`.

    Sources:
      - approved leave applications whose [start_date, end_date] cover `date`
      - staff attendance after configured cutoff that reports absent/missing

    The attendance signal is only *applied* when the cutoff has already
    elapsed for the given date (today or in the past); for future dates we
    skip the attendance signal.
    """
    cfg = await _get_proxy_config(db, tid)
    cutoff = cfg.get("cutoff_time") or "09:30"
    use_leave = cfg.get("use_leave_source", True)
    use_att = cfg.get("use_attendance_source", True)

    absent: dict[str, dict] = {}

    if use_leave:
        # Approved leaves overlapping `date`
        leaves = await db.leave_applications.find({
            "tenant_id": tid, "status": "approved",
            "start_date": {"$lte": date}, "end_date": {"$gte": date},
        }).to_list(500)
        for lv in leaves:
            emp = await db.employees.find_one({"_id": _oid(lv["employee_id"]), "tenant_id": tid})
            if not emp or not emp.get("user_id"): continue
            absent[emp["user_id"]] = {
                "teacher_user_id": emp["user_id"],
                "employee_id": str(emp["_id"]),
                "source": "leave",
                "leave_id": str(lv["_id"]),
                "reason": lv.get("reason"),
            }

    if use_att:
        # Attendance signal applies only when the cutoff has passed OR the date is historical.
        today = _today_iso()
        now_hhmm = _hhmm_now_utc()
        cutoff_passed = (date < today) or (date == today and now_hhmm >= cutoff)
        if cutoff_passed:
            # Find teachers (users with role teacher/class_teacher) that are
            # not already covered by leave absence AND are either explicitly
            # marked absent OR have no attendance row for the date.
            teachers = await db.users.find({
                "tenant_id": tid, "role": {"$in": ["teacher", "class_teacher"]},
                "status": "active",
            }).to_list(2000)
            for t in teachers:
                tu_id = str(t["_id"])
                if tu_id in absent: continue
                emp = await db.employees.find_one({"tenant_id": tid, "user_id": tu_id})
                if not emp: continue
                att = await db.staff_attendance.find_one({
                    "tenant_id": tid, "employee_id": str(emp["_id"]), "date": date,
                })
                if not att or att.get("status") in {"absent", "on_leave"}:
                    absent[tu_id] = {
                        "teacher_user_id": tu_id,
                        "employee_id": str(emp["_id"]),
                        "source": "attendance",
                        "reason": "unmarked_after_cutoff" if not att else att.get("status"),
                    }
    return absent


@router.get("/proxy/absences")
async def get_absences(
    date: str, academic_year_id: str,
    user: dict = Depends(require_permission(P_PROXY_VIEW)),
):
    db = get_db(); tid = user["tenant_id"]
    _weekday_of(date)
    absences = await _detect_absences(db, tid, date, academic_year_id)
    # For each absent teacher, compute affected periods (from master timetable on that weekday).
    wd = _weekday_of(date)
    rows: list[dict] = []
    for tu_id, meta in absences.items():
        slots = await db.timetable_slots.find({
            "tenant_id": tid, "academic_year_id": academic_year_id,
            "weekday": wd, "teacher_user_id": tu_id,
        }).sort("period_no", 1).to_list(100)
        # If a substitution is already approved for this slot/date, mark it covered.
        covered: dict[tuple[str, int], dict] = {}
        subs = await db.substitutions.find({
            "tenant_id": tid, "date": date, "original_teacher_user_id": tu_id,
            "status": {"$in": ["approved", "pending", "recommended"]},
        }).to_list(100)
        for s in subs:
            covered[(s.get("section_id"), s.get("period_no"))] = s
        affected = []
        for sl in slots:
            key = (sl.get("section_id"), sl.get("period_no"))
            affected.append({
                "slot": _out(sl),
                "substitution": _out(covered[key]) if key in covered else None,
            })
        teacher_user = await db.users.find_one({"_id": _oid(tu_id)})
        rows.append({
            **meta,
            "teacher": {
                "id": tu_id,
                "name": teacher_user.get("full_name") if teacher_user else None,
                "email": teacher_user.get("email") if teacher_user else None,
            } if teacher_user else {"id": tu_id},
            "affected_periods": affected,
        })
    return {"date": date, "weekday": wd, "absences": rows}


# ============================================================
# Proxy — ranking
# ============================================================
def _criterion(code: str, label: str, delta: float, hit: bool) -> dict:
    return {"code": code, "label": label, "delta": delta, "hit": hit}


async def _rank_candidates(
    db, tid: str, date: str, academic_year_id: str, wd: str, slot: dict, cfg: dict,
) -> list[dict]:
    """Score every eligible teacher for a given absent-teacher slot."""
    period_no = slot["period_no"]
    class_id = slot.get("class_id")
    subject_id = slot.get("subject_id")
    original_tu = slot.get("teacher_user_id")

    teachers = await db.users.find({
        "tenant_id": tid, "role": {"$in": ["teacher", "class_teacher"]},
        "status": "active",
    }).to_list(2000)

    # Pre-compute: this-period conflicts (any slot at same weekday+period_no)
    conflicts = await db.timetable_slots.find({
        "tenant_id": tid, "academic_year_id": academic_year_id,
        "weekday": wd, "period_no": period_no,
        "teacher_user_id": {"$ne": None},
    }).to_list(500)
    busy_teachers = {c["teacher_user_id"] for c in conflicts if c.get("teacher_user_id")}

    # Teachers already assigned a substitution at this same (section, period, date)
    sub_conflicts = await db.substitutions.find({
        "tenant_id": tid, "date": date, "period_no": period_no,
        "status": {"$in": ["approved", "pending", "recommended"]},
    }).to_list(500)
    busy_teachers.update({s["substitute_teacher_user_id"] for s in sub_conflicts})

    # Teachers who are themselves absent
    absences = await _detect_absences(db, tid, date, academic_year_id)
    absent_set = set(absences.keys())

    # Daily workload counts for ranking
    results: list[dict] = []
    for t in teachers:
        tu_id = str(t["_id"])
        if tu_id == original_tu: continue
        criteria: list[dict] = []
        hard_fail = False

        # Availability — must not be busy or absent
        avail = tu_id not in busy_teachers and tu_id not in absent_set
        criteria.append(_criterion("available", "Available at this period", 0, avail))
        if not avail:
            # Skip from results entirely — hard filter
            continue

        # Daily load — count master slots on that weekday for this teacher
        daily_load = await db.timetable_slots.count_documents({
            "tenant_id": tid, "academic_year_id": academic_year_id,
            "weekday": wd, "teacher_user_id": tu_id,
        })
        # Add existing proxy load on `date` for this teacher
        proxy_load = await db.substitutions.count_documents({
            "tenant_id": tid, "date": date,
            "substitute_teacher_user_id": tu_id,
            "status": {"$in": ["approved", "pending", "recommended"]},
        })
        criteria.append(_criterion("daily_load", f"Daily load: {daily_load} master + {proxy_load} proxy", 0, True))

        # Enforce max proxy per day cap
        if proxy_load >= cfg.get("max_proxy_per_day_per_teacher", 3):
            hard_fail = True
            criteria.append(_criterion("max_proxy_reached", f"Already at proxy cap ({proxy_load})", -100, True))
        if hard_fail: continue

        # Base score
        score = 50.0

        # Subject match (via TeacherAssignment or Employee.subjects_qualified)
        sub_match = False
        if subject_id:
            ta = await db.teacher_assignments.find_one({
                "tenant_id": tid, "academic_year_id": academic_year_id,
                "teacher_user_id": tu_id, "subject_id": subject_id,
            })
            if ta: sub_match = True
            else:
                emp = await db.employees.find_one({"tenant_id": tid, "user_id": tu_id})
                if emp and subject_id in (emp.get("subjects_qualified") or []):
                    sub_match = True
        if sub_match:
            score += 30
            criteria.append(_criterion("subject_match", "Qualified for this subject", 30, True))
        else:
            criteria.append(_criterion("subject_match", "Not a subject match", 0, False))
            if cfg.get("require_subject_match") and subject_id:
                continue   # hard filter

        # Same-grade preference
        same_grade = False
        if class_id:
            ta2 = await db.teacher_assignments.find_one({
                "tenant_id": tid, "academic_year_id": academic_year_id,
                "teacher_user_id": tu_id, "class_id": class_id,
            })
            if ta2: same_grade = True
        if same_grade:
            delta = 15 if cfg.get("prefer_same_grade", True) else 5
            score += delta
            criteria.append(_criterion("same_grade", "Already teaches this class", delta, True))

        # Workload penalty
        score -= 2 * daily_load
        score -= 5 * proxy_load
        criteria.append(_criterion("workload_penalty", f"-2×{daily_load} master, -5×{proxy_load} proxy", -(2*daily_load + 5*proxy_load), True))

        emp = await db.employees.find_one({"tenant_id": tid, "user_id": tu_id})
        results.append({
            "teacher_user_id": tu_id,
            "employee_id": str(emp["_id"]) if emp else None,
            "name": t.get("full_name") or t.get("email"),
            "email": t.get("email"),
            "role": t.get("role"),
            "rank_score": round(score, 2),
            "criteria": criteria,
            "daily_load": daily_load,
            "proxy_load": proxy_load,
            "subject_match": sub_match,
            "same_grade": same_grade,
        })

    results.sort(key=lambda r: r["rank_score"], reverse=True)
    return results


@router.get("/proxy/recommendations")
async def get_recommendations(
    date: str, academic_year_id: str,
    teacher_user_id: str,
    section_id: str | None = None,
    period_no: int | None = None,
    limit: int = 5,
    user: dict = Depends(require_permission(P_PROXY_VIEW)),
):
    db = get_db(); tid = user["tenant_id"]
    wd = _weekday_of(date)
    q: dict = {
        "tenant_id": tid, "academic_year_id": academic_year_id,
        "weekday": wd, "teacher_user_id": teacher_user_id,
    }
    if section_id: q["section_id"] = section_id
    if period_no is not None: q["period_no"] = period_no
    slots = await db.timetable_slots.find(q).sort("period_no", 1).to_list(100)
    if not slots:
        return {"affected": [], "cfg": _out(await _get_proxy_config(db, tid))}
    cfg = await _get_proxy_config(db, tid)
    affected = []
    for sl in slots:
        ranks = await _rank_candidates(db, tid, date, academic_year_id, wd, sl, cfg)
        affected.append({"slot": _out(sl), "candidates": ranks[:limit]})
    return {"affected": affected, "cfg": _out(cfg)}


# ============================================================
# Proxy — substitutions CRUD
# ============================================================
class CreateSubstitution(BaseModel):
    date: str
    academic_year_id: str
    timetable_slot_id: str | None = None     # when None, infer from (section, weekday, period)
    section_id: str | None = None
    period_no: int | None = None
    substitute_teacher_user_id: str
    source: str = "manual"                   # leave | attendance | manual
    notes: str | None = None
    auto_approve: bool = False               # when True, immediately approves if caller has perm


class DecisionIn(BaseModel):
    reason: str | None = None


async def _snapshot_from_slot(db, tid: str, p: dict) -> dict:
    """Resolve the master slot info into a Substitution snapshot."""
    wd = _weekday_of(p["date"])
    slot = None
    if p.get("timetable_slot_id"):
        slot = await db.timetable_slots.find_one({"_id": _oid(p["timetable_slot_id"]), "tenant_id": tid})
    elif p.get("section_id") and p.get("period_no") is not None:
        slot = await db.timetable_slots.find_one({
            "tenant_id": tid, "academic_year_id": p["academic_year_id"],
            "section_id": p["section_id"], "weekday": wd, "period_no": p["period_no"],
        })
    if not slot:
        raise HTTPException(status_code=404, detail="Timetable slot not found for the given date/section/period")
    return {
        "slot_id": str(slot["_id"]),
        "class_id": slot["class_id"],
        "section_id": slot["section_id"],
        "subject_id": slot.get("subject_id"),
        "original_teacher_user_id": slot.get("teacher_user_id"),
        "bell_schedule_id": slot["bell_schedule_id"],
        "weekday": slot["weekday"],
        "period_no": slot["period_no"],
    }


@router.post("/proxy/substitutions", status_code=201)
async def create_substitution(payload: CreateSubstitution, request: Request, user: dict = Depends(require_permission(P_PROXY_MANAGE))):
    db = get_db(); tid = user["tenant_id"]
    y = await _get_year(db, tid, payload.academic_year_id)
    if y.get("status") == "archived":
        raise HTTPException(status_code=409, detail={"code": "year_archived", "message": "Academic year is archived"})
    snap = await _snapshot_from_slot(db, tid, payload.model_dump())

    sub = await db.users.find_one({"_id": _oid(payload.substitute_teacher_user_id), "tenant_id": tid})
    if not sub or sub.get("role") not in {"teacher", "class_teacher"}:
        raise HTTPException(status_code=400, detail="substitute_teacher_user_id must reference a teacher")
    # Reject if substitute is also absent OR has a clash OR is the original teacher.
    if payload.substitute_teacher_user_id == snap["original_teacher_user_id"]:
        raise HTTPException(status_code=409, detail={"code": "same_teacher", "message": "Substitute cannot be the absent teacher"})
    clash = await db.timetable_slots.find_one({
        "tenant_id": tid, "academic_year_id": payload.academic_year_id,
        "weekday": snap["weekday"], "period_no": snap["period_no"],
        "teacher_user_id": payload.substitute_teacher_user_id,
    })
    if clash:
        raise HTTPException(status_code=409, detail={"code": "substitute_busy", "message": "Substitute has a class at this period", "slot_id": str(clash["_id"])})
    # Prevent duplicate substitution at same (section, period, date)
    dup = await db.substitutions.find_one({
        "tenant_id": tid, "date": payload.date,
        "section_id": snap["section_id"], "period_no": snap["period_no"],
        "status": {"$in": ["approved", "pending", "recommended"]},
    })
    if dup:
        raise HTTPException(status_code=409, detail={"code": "substitution_exists", "message": "A substitution already exists for this slot/date", "substitution_id": str(dup["_id"])})

    emp = await db.employees.find_one({"tenant_id": tid, "user_id": payload.substitute_teacher_user_id})
    user_perms = permissions_for(user.get("role", "")) | set(user.get("extra_permissions", []))
    can_auto_approve = payload.auto_approve and (P_PROXY_APPROVE in user_perms)
    status = "approved" if can_auto_approve else "pending"

    doc = Substitution(
        tenant_id=tid, date=payload.date, academic_year_id=payload.academic_year_id,
        weekday=snap["weekday"], period_no=snap["period_no"], bell_schedule_id=snap["bell_schedule_id"],
        timetable_slot_id=snap["slot_id"], class_id=snap["class_id"], section_id=snap["section_id"],
        subject_id=snap["subject_id"], original_teacher_user_id=snap["original_teacher_user_id"],
        substitute_teacher_user_id=payload.substitute_teacher_user_id,
        substitute_employee_id=str(emp["_id"]) if emp else None,
        status=status, source=payload.source,
        requested_by_user_id=user.get("id"),
        approved_by_user_id=user.get("id") if status == "approved" else None,
        approved_at=_now() if status == "approved" else None,
        notes=payload.notes,
    ).to_mongo()
    res = await db.substitutions.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="proxy.substitution.create", resource="substitution",
                    resource_id=str(res.inserted_id), tenant_id=tid,
                    actor=user, request=request,
                    new_value={"date": payload.date, "substitute": payload.substitute_teacher_user_id, "status": status})
    if status == "approved":
        await _notify_substitution(db, tid, doc, "approved")
    else:
        await _notify_substitution(db, tid, doc, "pending")
    return _out(doc)


@router.post("/proxy/substitutions/{sid}/approve")
async def approve_substitution(sid: str, payload: DecisionIn, request: Request, user: dict = Depends(require_permission(P_PROXY_APPROVE))):
    db = get_db(); tid = user["tenant_id"]
    sub = await db.substitutions.find_one({"_id": _oid(sid), "tenant_id": tid})
    if not sub: raise HTTPException(status_code=404, detail="Substitution not found")
    if sub.get("status") not in {"pending", "recommended"}:
        raise HTTPException(status_code=409, detail={"code": "invalid_state", "message": f"Cannot approve from status {sub.get('status')}"})
    await db.substitutions.update_one({"_id": sub["_id"]}, {"$set": {
        "status": "approved", "approved_by_user_id": user.get("id"),
        "approved_at": _now(), "decision_reason": payload.reason, "updated_at": _now(),
    }})
    new = await db.substitutions.find_one({"_id": sub["_id"]})
    await log_event(action="proxy.substitution.approve", resource="substitution",
                    resource_id=sid, tenant_id=tid, actor=user, request=request)
    await _notify_substitution(db, tid, new, "approved")
    return _out(new)


@router.post("/proxy/substitutions/{sid}/reject")
async def reject_substitution(sid: str, payload: DecisionIn, request: Request, user: dict = Depends(require_permission(P_PROXY_APPROVE))):
    db = get_db(); tid = user["tenant_id"]
    sub = await db.substitutions.find_one({"_id": _oid(sid), "tenant_id": tid})
    if not sub: raise HTTPException(status_code=404, detail="Substitution not found")
    if sub.get("status") not in {"pending", "recommended"}:
        raise HTTPException(status_code=409, detail={"code": "invalid_state", "message": f"Cannot reject from status {sub.get('status')}"})
    await db.substitutions.update_one({"_id": sub["_id"]}, {"$set": {
        "status": "rejected", "rejected_by_user_id": user.get("id"),
        "decision_reason": payload.reason, "updated_at": _now(),
    }})
    await log_event(action="proxy.substitution.reject", resource="substitution",
                    resource_id=sid, tenant_id=tid, actor=user, request=request)
    return _out(await db.substitutions.find_one({"_id": sub["_id"]}))


@router.post("/proxy/substitutions/{sid}/cancel")
async def cancel_substitution(sid: str, payload: DecisionIn, request: Request, user: dict = Depends(require_permission(P_PROXY_MANAGE))):
    db = get_db(); tid = user["tenant_id"]
    sub = await db.substitutions.find_one({"_id": _oid(sid), "tenant_id": tid})
    if not sub: raise HTTPException(status_code=404, detail="Substitution not found")
    if sub.get("status") == "cancelled":
        return _out(sub)
    await db.substitutions.update_one({"_id": sub["_id"]}, {"$set": {
        "status": "cancelled", "cancelled_at": _now(),
        "decision_reason": payload.reason, "updated_at": _now(),
    }})
    await log_event(action="proxy.substitution.cancel", resource="substitution",
                    resource_id=sid, tenant_id=tid, actor=user, request=request)
    return _out(await db.substitutions.find_one({"_id": sub["_id"]}))


@router.get("/proxy/substitutions")
async def list_substitutions(
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    substitute_teacher_user_id: str | None = None,
    original_teacher_user_id: str | None = None,
    section_id: str | None = None,
    user: dict = Depends(require_permission(P_PROXY_VIEW)),
):
    db = get_db(); tid = user["tenant_id"]
    q: dict = {"tenant_id": tid}
    if date: q["date"] = date
    elif date_from or date_to:
        rng: dict = {}
        if date_from: rng["$gte"] = date_from
        if date_to: rng["$lte"] = date_to
        q["date"] = rng
    if status: q["status"] = status
    if substitute_teacher_user_id: q["substitute_teacher_user_id"] = substitute_teacher_user_id
    if original_teacher_user_id: q["original_teacher_user_id"] = original_teacher_user_id
    if section_id: q["section_id"] = section_id
    docs = await db.substitutions.find(q).sort([("date", -1), ("period_no", 1)]).to_list(500)
    return [_out(d) for d in docs]


async def _notify_substitution(db, tid: str, sub: dict, event: str) -> None:
    """Fire in-app alerts for the configured stakeholders."""
    cfg = await _get_proxy_config(db, tid)
    title = {
        "pending": "Substitution requested",
        "approved": "Substitution confirmed",
    }.get(event, f"Substitution {event}")
    section = await db.academic_sections.find_one({"_id": _oid(sub["section_id"]), "tenant_id": tid})
    section_name = section.get("name") if section else sub["section_id"]
    msg = (f"{title} — {sub['date']} P{sub['period_no']} • Section {section_name}. "
           f"Substitute: {sub['substitute_teacher_user_id']}")
    if cfg.get("notify_substitute"):
        await create_alert(title=title, message=msg, level="info", tenant_id=tid,
                           resource="substitution", resource_id=str(sub["_id"]))
    if cfg.get("notify_admin") or cfg.get("notify_class_teacher"):
        await create_alert(title=title, message=msg, level="info", tenant_id=tid,
                           resource="substitution", resource_id=str(sub["_id"]))
